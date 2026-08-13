"""Тесты Этапа 1 ТЗ: импорт готового summary.csv без Monte-Carlo вычислений."""

import csv
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.experiment import Base, ExperimentSource, ExperimentStatus
from app.services import csv_import, experiment_manager
from app.services.csv_import import CsvValidationError, parse_and_validate_csv
from app.services.results_reader import read_summary, result_schema


REQUIRED_FIELDS = [
    "code_name",
    "code_family",
    "n",
    "k",
    "decoder",
    "ebn0_db",
    "message_count",
    "ber",
    "frame_error_rate",
    "success_count",
    "failure_count",
    "frame_errors",
    "bit_errors",
    "total_bits",
    "skipped",
]


def _make_csv_bytes(rows: list[dict[str, object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REQUIRED_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _valid_row(**overrides: object) -> dict[str, object]:
    row = {
        "code_name": "wavelet_16_8",
        "code_family": "wavelet",
        "n": 16,
        "k": 8,
        "decoder": "syndrome",
        "ebn0_db": 2.0,
        "message_count": 100,
        "ber": 0.01,
        "frame_error_rate": 0.1,
        "success_count": 90,
        "failure_count": 10,
        "frame_errors": 10,
        "bit_errors": 8,
        "total_bits": 800,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_missing_required_column_is_rejected() -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["code_name", "n", "k"])
    writer.writeheader()
    writer.writerow({"code_name": "wavelet", "n": 16, "k": 8})

    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(buffer.getvalue().encode("utf-8"))

    assert any("Missing required column" in error for error in excinfo.value.errors)


def test_empty_csv_is_rejected() -> None:
    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(b"")
    assert excinfo.value.errors


def test_csv_with_header_only_is_rejected() -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REQUIRED_FIELDS)
    writer.writeheader()

    with pytest.raises(CsvValidationError):
        parse_and_validate_csv(buffer.getvalue().encode("utf-8"))


def test_malformed_bytes_are_rejected() -> None:
    with pytest.raises(CsvValidationError):
        parse_and_validate_csv(b"\xff\xfe\x00not-utf8")


# ---------------------------------------------------------------------------
# Semantic validation
# ---------------------------------------------------------------------------


def test_valid_csv_passes_validation() -> None:
    raw = _make_csv_bytes([_valid_row()])
    result = parse_and_validate_csv(raw)
    assert len(result.rows) == 1
    assert result.rows[0]["code_name"] == "wavelet_16_8"


def test_invalid_ber_out_of_range_is_rejected() -> None:
    raw = _make_csv_bytes([_valid_row(ber=1.42)])
    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(raw)
    assert any("Invalid BER" in error for error in excinfo.value.errors)


def test_invalid_fer_out_of_range_is_rejected() -> None:
    raw = _make_csv_bytes([_valid_row(frame_error_rate=1.42)])
    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(raw)
    assert any("Invalid FER" in error for error in excinfo.value.errors)


def test_k_greater_than_n_is_rejected() -> None:
    raw = _make_csv_bytes([_valid_row(n=8, k=16)])
    with pytest.raises(CsvValidationError):
        parse_and_validate_csv(raw)


def test_success_failure_mismatch_is_rejected() -> None:
    raw = _make_csv_bytes([_valid_row(success_count=50, failure_count=10)])
    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(raw)
    assert any("success_count" in error for error in excinfo.value.errors)


def test_frame_error_rate_inconsistent_with_frame_errors_is_rejected() -> None:
    raw = _make_csv_bytes([_valid_row(frame_errors=99, frame_error_rate=0.1)])
    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(raw)
    assert any("frame_error_rate" in error for error in excinfo.value.errors)


def test_ber_inconsistent_with_bit_errors_is_rejected() -> None:
    raw = _make_csv_bytes([_valid_row(bit_errors=500, total_bits=800, ber=0.01)])
    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(raw)
    assert any("ber=" in error for error in excinfo.value.errors)


def test_message_count_mismatch_within_same_group_is_rejected() -> None:
    rows = [
        _valid_row(decoder="syndrome", message_count=100),
        _valid_row(decoder="chase", message_count=50),
    ]
    raw = _make_csv_bytes(rows)
    with pytest.raises(CsvValidationError) as excinfo:
        parse_and_validate_csv(raw)
    assert any("message_count" in error for error in excinfo.value.errors)


def test_skipped_rows_are_not_range_checked() -> None:
    raw = _make_csv_bytes(
        [_valid_row(ber="", frame_error_rate="", **{"skipped": "true"})]  # type: ignore[arg-type]
    )
    # skipped-строки без метрик не должны считаться ошибкой диапазона.
    result = parse_and_validate_csv(raw)
    assert result.rows[0]["ber"] is None


# ---------------------------------------------------------------------------
# build_synthetic_config
# ---------------------------------------------------------------------------


def test_build_synthetic_config_derives_only_known_fields() -> None:
    raw = _make_csv_bytes(
        [
            _valid_row(code_name="wavelet_16_8", ebn0_db=0.0, message_count=100),
            _valid_row(code_name="wavelet_16_8", ebn0_db=2.0, message_count=100),
            _valid_row(code_name="bch_derived_16_8", code_family="bch_derived", ebn0_db=0.0),
        ]
    )
    result = parse_and_validate_csv(raw)
    config = csv_import.build_synthetic_config(result.rows, results_dir="/tmp/x")

    assert config["results_dir"] == "/tmp/x"
    assert sorted(config["ebn0_db_values"]) == [0.0, 2.0]
    names = {code["name"] for code in config["codes"]}
    assert names == {"wavelet_16_8", "bch_derived_16_8"}


# ---------------------------------------------------------------------------
# Integration: ExperimentManager.import_csv (изолированная БД/каталог)
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Подменяет SessionLocal и results dir на изолированные для теста."""
    db_path = tmp_path / "test_experiments.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    test_session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    monkeypatch.setattr(experiment_manager, "SessionLocal", test_session_local)
    monkeypatch.setattr(
        experiment_manager,
        "make_results_dir",
        lambda experiment_id, name, subdir=None: str(
            tmp_path / "results" / f"{experiment_id.hex[:12]}_{name}"
        ),
    )
    return experiment_manager.manager, test_session_local


def test_import_csv_creates_completed_experiment(isolated_manager) -> None:
    manager, test_session_local = isolated_manager
    raw = _make_csv_bytes([_valid_row()])

    experiment = manager.import_csv(
        name="Imported test",
        description="from unit test",
        filename="summary.csv",
        raw_bytes=raw,
    )

    assert experiment.status == ExperimentStatus.completed
    assert experiment.source == ExperimentSource.imported_csv
    assert experiment.original_filename == "summary.csv"

    # Появляется в БД.
    with test_session_local() as session:
        from app.models.experiment import Experiment

        stored = session.get(Experiment, experiment.id)
        assert stored is not None
        assert stored.source == ExperimentSource.imported_csv

    # Существующие читатели результатов должны работать без изменений.
    columns, rows = read_summary(experiment.results_dir)
    assert "code_name" in columns
    assert rows[0]["code_name"] == "wavelet_16_8"

    schema = result_schema(experiment.results_dir)
    assert schema["codes"] == ["wavelet_16_8"]


def test_import_csv_rejects_invalid_csv_without_creating_experiment(isolated_manager) -> None:
    manager, test_session_local = isolated_manager
    raw = _make_csv_bytes([_valid_row(ber=5.0)])

    with pytest.raises(CsvValidationError):
        manager.import_csv(
            name="Bad import",
            description="",
            filename="bad.csv",
            raw_bytes=raw,
        )

    with test_session_local() as session:
        from app.models.experiment import Experiment

        assert session.query(Experiment).count() == 0


# ---------------------------------------------------------------------------
# API-level round trip
# ---------------------------------------------------------------------------


def test_import_csv_api_endpoint(isolated_manager) -> None:
    from app.main import app

    raw = _make_csv_bytes([_valid_row()])
    client = TestClient(app)

    response = client.post(
        "/api/experiments/import/csv",
        files={"file": ("summary.csv", raw, "text/csv")},
        data={"name": "API import", "description": "via TestClient"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["source"] == "imported_csv"
    assert payload["status"] == "completed"
    assert payload["runtime_config_available"] is False

    experiment_id = payload["id"]
    schema_response = client.get(f"/api/experiments/{experiment_id}/results/schema")
    assert schema_response.status_code == 200
    assert schema_response.json()["codes"] == ["wavelet_16_8"]


def test_import_csv_api_endpoint_rejects_invalid_csv(isolated_manager) -> None:
    from app.main import app

    raw = _make_csv_bytes([_valid_row(ber=1.5)])
    client = TestClient(app)

    response = client.post(
        "/api/experiments/import/csv",
        files={"file": ("summary.csv", raw, "text/csv")},
        data={"name": "Bad API import", "description": ""},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "errors" in detail
    assert any("Invalid BER" in message for message in detail["errors"])
