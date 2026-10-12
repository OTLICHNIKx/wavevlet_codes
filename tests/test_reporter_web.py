"""Тесты веб-интерфейса репортера.

Проверяем сквозной сценарий: главная страница -> загрузка CSV ->
HTML-отчёт с встроенными графиками, плюс обработку ошибок.
"""

from __future__ import annotations

import io
import re

import pytest

flask = pytest.importorskip("flask")

from reporter.web import app, _detect_format  # noqa: E402


BULK_HEADER = (
    "code_name,code_family,n,k,ebn0_db,message_count,decoder,"
    "skipped,ber\n"
)
BULK_ROWS = "".join(
    f"{name},{family},32,16,{snr},20000,{decoder},False,{ber}\n"
    for name, family, ber in (
        ("wavelet_32_16", "wavelet", "0.001"),
        ("wavelet_32_16", "wavelet", "0.010"),
        ("bch_derived_32_16", "bch_derived", "0.005"),
        ("bch_derived_32_16", "bch_derived", "0.008"),
    )
    for snr, decoder in ((0.0, "syndrome"), (5.0, "syndrome"))
    if True
    for ber in [ber]
)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_renders_upload_form(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'name="csv_file"' in body
    assert 'name="channel"' in body


def test_detect_format_by_header() -> None:
    assert _detect_format(["code_name", "n", "k", "ebn0_db", "ber"]) == "bulk"
    assert _detect_format(["code", "metric", "mean_BER"]) == "mc"
    assert _detect_format(["foo", "bar"]) == "unknown"


def test_bulk_upload_produces_report_with_embedded_charts(client) -> None:
    payload = (BULK_HEADER + BULK_ROWS).encode("utf-8")
    response = client.post(
        "/",
        data={
            "csv_file": (io.BytesIO(payload), "summary.csv"),
            "channel": "rayleigh",
            "experiment": "unit_test",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "Отчёт: преимущество Wavelet" in body
    # графики встроены как base64, а не отдаются отдельными файлами
    assert "data:image/png;base64" in body
    # есть сводные карточки и таблицы
    assert re.search(r'<div class="v">[^<]+</div>', body)
    assert "Свод по конкурентам" in body


def test_bulk_upload_without_channel_shows_error(client) -> None:
    payload = (BULK_HEADER + BULK_ROWS).encode("utf-8")
    response = client.post(
        "/",
        data={"csv_file": (io.BytesIO(payload), "summary.csv"), "channel": ""},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "нужно указать канал" in response.get_data(as_text=True)


def test_unknown_format_shows_error(client) -> None:
    response = client.post(
        "/",
        data={"csv_file": (io.BytesIO(b"foo,bar\n1,2\n"), "bad.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Не удалось определить формат" in response.get_data(as_text=True)


def test_missing_file_shows_error(client) -> None:
    response = client.post(
        "/", data={}, content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "не выбран" in response.get_data(as_text=True)


def test_empty_file_shows_error(client) -> None:
    response = client.post(
        "/",
        data={"csv_file": (io.BytesIO(b""), "empty.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Не удалось определить формат" in body
