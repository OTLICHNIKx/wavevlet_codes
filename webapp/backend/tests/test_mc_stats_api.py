from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(monkeypatch, tmp_path: Path):
    stats = tmp_path / "results"
    stats.mkdir()
    (stats / "wavelet_channel_decoder_statistics_all_metrics.csv").write_text(
        VALID_CSV,
        encoding="utf-8",
    )
    (stats / "wavelet_channel_decoder_statistics.csv").write_text(
        "code,channel,decoder,parameter,mean_BER\n"
        "wavelet_16_8,awgn,syndrome,0.0,0.30\n",
        encoding="utf-8",
    )
    (stats / "unrelated.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setenv("MC_STATS_DIR", str(stats))
    monkeypatch.setenv("MC_STATS_UPLOADS_DIR", str(uploads))
    with TestClient(app) as test_client:
        yield test_client


VALID_CSV = """code,channel,decoder,parameter,metric,mean,std,ci_low,ci_high,seeds,words
wavelet_16_8,awgn,syndrome,0.0,ber,0.30,0.01,0.28,0.32,5,100
wavelet_16_8,awgn,syndrome,1.0,ber,0.20,0.01,0.18,0.22,5,100
wavelet_16_8,awgn,chase,0.0,ber,0.10,0.02,0.07,0.13,5,100
wavelet_16_8,awgn,chase,1.0,ber,0.05,0.01,0.03,0.07,5,100
wavelet_16_8,rayleigh,syndrome,0.0,ber,0.40,0.02,0.37,0.43,5,100
wavelet_16_8,rayleigh,syndrome,1.0,frame_error_rate,0.5,0.05,0.4,0.6,5,100
ldpc_32_16,awgn,syndrome,0.0,ber,0.22,0.01,0.20,0.24,5,100
ldpc_32_16,awgn,chase,0.0,ber,0.08,0.01,0.06,0.10,5,100
"""


def test_mc_stats_lists_only_statistics_csv(client) -> None:
    response = client.get("/api/mc-stats")
    assert response.status_code == 200
    body = response.json()
    assert body["files"] == [
        "wavelet_channel_decoder_statistics_all_metrics.csv"
    ]
    assert body["items"][0]["source"] == "results"


def test_mc_stats_series_grouped_by_decoder(client) -> None:
    response = client.get(
        "/api/mc-stats/series",
        params={"code": "wavelet_16_8", "channel": "awgn", "metric": "ber"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["universe"]["codes"] == ["ldpc_32_16", "wavelet_16_8"]
    assert body["universe"]["channels"] == ["awgn", "rayleigh"]
    assert body["universe"]["metrics"] == ["ber", "frame_error_rate"]
    by_decoder = {item["decoder"]: item for item in body["series"]}
    assert set(by_decoder) == {"syndrome", "chase"}
    assert by_decoder["syndrome"]["x"] == [0.0, 1.0]
    assert by_decoder["syndrome"]["y"] == [0.30, 0.20]
    assert by_decoder["syndrome"]["ci_low"] == [0.28, 0.18]
    assert by_decoder["syndrome"]["ci_high"] == [0.32, 0.22]
    assert by_decoder["syndrome"]["seeds"] == 5
    assert by_decoder["syndrome"]["words"] == 100


def test_mc_stats_series_filters_channel(client) -> None:
    body = client.get(
        "/api/mc-stats/series",
        params={"channel": "rayleigh", "metric": "frame_error_rate"},
    ).json()
    assert [item["decoder"] for item in body["series"]] == ["syndrome"]
    assert body["series"][0]["y"] == [0.5]


def test_mc_stats_series_decoders_param(client) -> None:
    body = client.get(
        "/api/mc-stats/series",
        params={
            "code": "wavelet_16_8", "channel": "awgn", "metric": "ber",
            "decoders": "syndrome,chase",
        },
    ).json()
    assert {item["decoder"] for item in body["series"]} == {"syndrome", "chase"}
    solo = client.get(
        "/api/mc-stats/series",
        params={
            "code": "wavelet_16_8", "channel": "awgn", "metric": "ber",
            "decoders": "chase",
        },
    ).json()
    assert [item["decoder"] for item in solo["series"]] == ["chase"]


def test_mc_stats_series_multiple_codes(client) -> None:
    body = client.get(
        "/api/mc-stats/series",
        params={"channel": "awgn", "metric": "ber"},
    ).json()
    pairs = {(item["code"], item["decoder"]) for item in body["series"]}
    assert ("wavelet_16_8", "syndrome") in pairs
    assert ("ldpc_32_16", "chase") in pairs
    only_ldpc = client.get(
        "/api/mc-stats/series",
        params={"channel": "awgn", "metric": "ber",
                "codes": "ldpc_32_16"},
    ).json()
    assert {item["code"] for item in only_ldpc["series"]} == {"ldpc_32_16"}


def test_mc_stats_rejects_unknown_file(client) -> None:
    response = client.get(
        "/api/mc-stats/series", params={"file": "../secrets.csv"},
    )
    assert response.status_code == 404


def test_mc_stats_upload_delete_flow(client) -> None:
    files = client.get("/api/mc-stats").json()
    assert len(files["items"]) == 1

    upload = client.post(
        "/api/mc-stats/upload",
        files={"file": ("my_mc.csv", VALID_CSV, "text/csv")},
        data={"name": "Мой MC тест"},
    )
    assert upload.status_code == 201, upload.text
    stored = upload.json()["name"]
    assert stored.endswith("_statistics_all_metrics.csv")

    listing = client.get("/api/mc-stats").json()
    names = {item["name"] for item in listing["items"]}
    assert stored in names
    source = {item["name"]: item["source"] for item in listing["items"]}[stored]
    assert source == "uploaded"

    series = client.get(
        "/api/mc-stats/series", params={"file": stored}
    ).json()
    assert series["file"] == stored
    assert "wavelet_16_8" in series["universe"]["codes"]

    reject_repo = client.delete(
        "/api/mc-stats/files/wavelet_channel_decoder_statistics_all_metrics.csv"
    )
    assert reject_repo.status_code == 403

    delete = client.delete(f"/api/mc-stats/files/{stored}")
    assert delete.status_code == 200
    after = client.get("/api/mc-stats").json()
    assert {item["name"] for item in after["items"]} == {
        "wavelet_channel_decoder_statistics_all_metrics.csv"
    }


def test_mc_stats_upload_validation(client) -> None:
    bad = client.post(
        "/api/mc-stats/upload",
        files={"file": ("junk.csv", "a,b\n1,2\n", "text/csv")},
        data={"name": "junk"},
    )
    assert bad.status_code == 422

    not_csv = client.post(
        "/api/mc-stats/upload",
        files={"file": ("data.txt", VALID_CSV, "text/plain")},
        data={"name": "txt"},
    )
    assert not_csv.status_code == 422

    empty = client.post(
        "/api/mc-stats/upload",
        files={"file": ("empty.csv", "", "text/csv")},
        data={"name": "empty"},
    )
    assert empty.status_code == 422
