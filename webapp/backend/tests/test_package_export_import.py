"""Тесты Этапа 2 ТЗ: экспорт/импорт portable experiment package (.zip)."""

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.experiment import Base, Experiment, ExperimentSource, ExperimentStatus
from app.services import experiment_manager
from app.services.package_io import (
    PACKAGE_FORMAT,
    SCHEMA_VERSION,
    PackageValidationError,
    build_manifest,
    build_zip,
    parse_and_validate_package,
)


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
    }
    row.update(overrides)
    return row


def _valid_manifest(**overrides: object) -> dict[str, object]:
    manifest = build_manifest(
        name="Test experiment",
        created_at="2026-01-01T00:00:00",
        status="completed",
        experiment_id="fixed-id",
    )
    manifest.update(overrides)
    return manifest


def _make_zip(
    *,
    manifest: dict[str, object] | None = None,
    summary_bytes: bytes | None = None,
    extra_members: dict[str, bytes] | None = None,
    skip_manifest: bool = False,
    skip_summary: bool = False,
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        if not skip_manifest:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest if manifest is not None else _valid_manifest()),
            )
        if not skip_summary:
            archive.writestr(
                "summary.csv",
                summary_bytes if summary_bytes is not None else _make_csv_bytes([_valid_row()]),
            )
        for name, content in (extra_members or {}).items():
            archive.writestr(name, content)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Manifest / schema validation
# ---------------------------------------------------------------------------


def test_valid_package_parses_successfully() -> None:
    raw = _make_zip()
    parsed = parse_and_validate_package(raw)
    assert parsed.manifest["format"] == PACKAGE_FORMAT
    assert len(parsed.summary_rows) == 1


def test_missing_manifest_is_rejected() -> None:
    raw = _make_zip(skip_manifest=True)
    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)
    assert any("manifest.json" in error for error in excinfo.value.errors)


def test_missing_summary_csv_is_rejected() -> None:
    raw = _make_zip(skip_summary=True)
    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)
    assert any("summary.csv" in error for error in excinfo.value.errors)


def test_unsupported_schema_version_is_rejected() -> None:
    raw = _make_zip(manifest=_valid_manifest(schema_version=999))
    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)
    assert any("Unsupported experiment package version" in error for error in excinfo.value.errors)


def test_unknown_format_is_rejected() -> None:
    raw = _make_zip(manifest=_valid_manifest(format="something-else"))
    with pytest.raises(PackageValidationError):
        parse_and_validate_package(raw)


def test_invalid_csv_inside_package_is_rejected() -> None:
    raw = _make_zip(summary_bytes=_make_csv_bytes([_valid_row(ber=5.0)]))
    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)
    assert any("Invalid BER" in error for error in excinfo.value.errors)


def test_optional_files_are_parsed_when_present() -> None:
    runtime_config = {"message_count": 100, "codes": []}
    code_metadata = [{"name": "wavelet_16_8", "family": "wavelet", "n": 16, "k": 8}]
    raw = _make_zip(
        extra_members={
            "runtime_config.json": json.dumps(runtime_config).encode("utf-8"),
            "code_metadata.json": json.dumps(code_metadata).encode("utf-8"),
            "experiment.log": b"line 1\nline 2\n",
        }
    )
    parsed = parse_and_validate_package(raw)
    assert parsed.runtime_config == runtime_config
    assert parsed.code_metadata == code_metadata
    assert parsed.experiment_log == "line 1\nline 2\n"


def test_malformed_runtime_config_is_rejected() -> None:
    raw = _make_zip(extra_members={"runtime_config.json": b"{not valid json"})
    with pytest.raises(PackageValidationError):
        parse_and_validate_package(raw)


def test_non_object_runtime_config_is_rejected() -> None:
    raw = _make_zip(extra_members={"runtime_config.json": b"[]"})
    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)
    assert any("JSON-объектом" in error for error in excinfo.value.errors)


def test_invalid_code_metadata_shape_is_rejected() -> None:
    raw = _make_zip(extra_members={"code_metadata.json": b"{}"})
    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)
    assert any("массивом JSON-объектов" in error for error in excinfo.value.errors)


# ---------------------------------------------------------------------------
# ZIP safety
# ---------------------------------------------------------------------------


def test_empty_package_is_rejected() -> None:
    with pytest.raises(PackageValidationError):
        parse_and_validate_package(b"")


def test_not_a_zip_is_rejected() -> None:
    with pytest.raises(PackageValidationError):
        parse_and_validate_package(b"this is definitely not a zip file")


@pytest.mark.parametrize(
    "unsafe_name",
    ["../evil.txt", "/absolute/evil.txt", "../../etc/passwd", "C:/evil.txt", "..\\evil.txt"],
)
def test_path_traversal_and_absolute_entries_are_rejected(unsafe_name: str) -> None:
    raw = _make_zip(extra_members={unsafe_name: b"pwned"})

    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)

    assert any("Недопустимый путь" in error for error in excinfo.value.errors)


def test_unknown_file_type_is_rejected() -> None:
    raw = _make_zip(extra_members={"payload.py": b"print('no')"})

    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(raw)

    assert any("Недопустимый файл" in error for error in excinfo.value.errors)


def test_duplicate_required_member_is_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        archive.writestr("manifest.json", json.dumps(_valid_manifest()))
        archive.writestr("summary.csv", _make_csv_bytes([_valid_row()]))
        archive.writestr("summary.csv", _make_csv_bytes([_valid_row(ber=0.02)]))

    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(buffer.getvalue())

    assert any("несколько раз" in error for error in excinfo.value.errors)


def test_too_many_files_is_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        archive.writestr("manifest.json", json.dumps(_valid_manifest()))
        archive.writestr("summary.csv", _make_csv_bytes([_valid_row()]))
        for index in range(300):
            archive.writestr(f"junk_{index}.txt", b"x")

    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(buffer.getvalue())
    assert any("слишком много файлов" in error for error in excinfo.value.errors)


def test_oversized_declared_payload_is_rejected() -> None:
    """
    Заявленный (uncompressed) размер известного файла превышает лимит.

    Исходный байт-паттерн классической zip-бомбы: огромный
    uncompressed-размер из высокосжимаемых данных, а не искусственная
    подделка метаданных (zipfile всё равно пересчитывает file_size при
    записи, так что подделать его напрямую невозможно).
    """
    huge_but_compressible = b"0" * (70 * 1024 * 1024)  # 70 MiB нулей > MAX_MEMBER_BYTES

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(_valid_manifest()))
        archive.writestr("summary.csv", huge_but_compressible)

    with pytest.raises(PackageValidationError) as excinfo:
        parse_and_validate_package(buffer.getvalue())
    assert any("превышает допустимый размер" in error for error in excinfo.value.errors)


def test_oversized_upload_is_rejected() -> None:
    huge = b"0" * (101 * 1024 * 1024)
    with pytest.raises(PackageValidationError):
        parse_and_validate_package(huge)


# ---------------------------------------------------------------------------
# build_zip round trip
# ---------------------------------------------------------------------------


def test_build_zip_round_trips_through_parse() -> None:
    manifest = _valid_manifest()
    raw = build_zip(
        manifest=manifest,
        summary_csv_bytes=_make_csv_bytes([_valid_row()]),
        runtime_config_bytes=json.dumps({"message_count": 5}).encode("utf-8"),
        code_metadata_bytes=json.dumps([{"name": "wavelet_16_8"}]).encode("utf-8"),
        experiment_log_bytes=b"hello\n",
    )
    parsed = parse_and_validate_package(raw)
    assert parsed.manifest == manifest
    assert parsed.runtime_config == {"message_count": 5}
    assert parsed.code_metadata == [{"name": "wavelet_16_8"}]
    assert parsed.experiment_log == "hello\n"


# ---------------------------------------------------------------------------
# Integration: ExperimentManager (изолированная БД/каталог)
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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


def test_import_package_creates_completed_experiment_with_runtime_config(
    isolated_manager,
) -> None:
    manager, _ = isolated_manager
    runtime_config = {
        "message_count": 100,
        "codes": [{"name": "wavelet_16_8", "family": "wavelet", "n": 16, "k": 8}],
    }
    raw = build_zip(
        manifest=_valid_manifest(name="Round trip experiment"),
        summary_csv_bytes=_make_csv_bytes([_valid_row()]),
        runtime_config_bytes=json.dumps(runtime_config).encode("utf-8"),
        code_metadata_bytes=None,
        experiment_log_bytes=b"log line\n",
    )

    experiment = manager.import_package(
        name="", description="", filename="pkg.zip", raw_bytes=raw
    )

    assert experiment.status == ExperimentStatus.completed
    assert experiment.source == ExperimentSource.imported_package
    # Имя по умолчанию взято из manifest, если пользователь не указал своё.
    assert experiment.name == "Round trip experiment"
    assert manager.has_runtime_config(experiment)
    assert manager.has_experiment_log(experiment)
    assert json.loads(experiment.config_json) == runtime_config
    assert manager.log(experiment, tail=10) == ["log line"]


def test_import_package_without_runtime_config_marks_unavailable(isolated_manager) -> None:
    manager, _ = isolated_manager
    raw = build_zip(
        manifest=_valid_manifest(),
        summary_csv_bytes=_make_csv_bytes([_valid_row()]),
        runtime_config_bytes=None,
        code_metadata_bytes=None,
        experiment_log_bytes=None,
    )

    experiment = manager.import_package(
        name="My import", description="", filename="pkg.zip", raw_bytes=raw
    )

    assert not manager.has_runtime_config(experiment)
    assert not manager.has_experiment_log(experiment)
    config = json.loads(experiment.config_json)
    assert config["codes"][0]["name"] == "wavelet_16_8"


def test_export_then_import_round_trip_preserves_data(isolated_manager) -> None:
    manager, test_session_local = isolated_manager

    runtime_config = {
        "message_count": 100,
        "message_seed": 1,
        "noise_seed": 2,
        "ebn0_db_values": [2.0],
        "codes": [
            {
                "name": "wavelet_16_8",
                "family": "wavelet",
                "n": 16,
                "k": 8,
            }
        ],
        "decoders": {
            "run_syndrome": True,
            "run_hard_mld": False,
            "run_soft_mld": False,
            "run_chase": False,
            "syndrome_max_error_weight": 1,
            "chase_inner_decoder_max_error_weight": 1,
            "chase_unreliable_positions_count": 4,
            "max_k_for_mld": 16,
        },
        "results_dir": "irrelevant",
    }

    # Симулируем completed local experiment: пишем summary.csv +
    # runtime_config.json прямо в results_dir, минуя реальный runner.
    csv_bytes = _make_csv_bytes([_valid_row()])
    local_results_dir = manager.import_csv(  # используем import_csv как удобный способ создать директорию с summary.csv
        name="source experiment",
        description="",
        filename="summary.csv",
        raw_bytes=csv_bytes,
    ).results_dir
    (Path(local_results_dir) / "runtime_config.json").write_text(
        json.dumps(runtime_config), encoding="utf-8"
    )

    with test_session_local() as session:
        original = (
            session.query(Experiment)
            .filter(Experiment.results_dir == local_results_dir)
            .one()
        )
        original.source = ExperimentSource.local
        session.commit()
        session.refresh(original)

    exported_bytes = manager.export_package(original)

    with zipfile.ZipFile(io.BytesIO(exported_bytes)) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "summary.csv", "runtime_config.json", "code_metadata.json"} <= names

    imported = manager.import_package(
        name="", description="", filename="roundtrip.zip", raw_bytes=exported_bytes
    )

    assert imported.id != original.id
    assert imported.name == original.name
    assert json.loads(imported.config_json) == runtime_config

    from app.services.results_reader import read_summary

    original_columns, original_rows = read_summary(original.results_dir)
    imported_columns, imported_rows = read_summary(imported.results_dir)
    assert original_columns == imported_columns
    assert original_rows == imported_rows


def test_import_package_rejects_invalid_zip_without_creating_experiment(
    isolated_manager,
) -> None:
    manager, test_session_local = isolated_manager
    raw = _make_zip(skip_manifest=True)

    with pytest.raises(PackageValidationError):
        manager.import_package(
            name="bad", description="", filename="bad.zip", raw_bytes=raw
        )

    with test_session_local() as session:
        count = (
            session.query(Experiment)
            .filter(Experiment.source == ExperimentSource.imported_package)
            .count()
        )
        assert count == 0


# ---------------------------------------------------------------------------
# API-level round trip
# ---------------------------------------------------------------------------


def test_export_and_import_package_via_api(isolated_manager) -> None:
    from app.main import app

    manager, _ = isolated_manager
    client = TestClient(app)

    csv_response = client.post(
        "/api/experiments/import/csv",
        files={"file": ("summary.csv", _make_csv_bytes([_valid_row()]), "text/csv")},
        data={"name": "API source experiment", "description": ""},
    )
    assert csv_response.status_code == 201, csv_response.text
    source_id = csv_response.json()["id"]

    export_response = client.get(f"/api/experiments/{source_id}/export")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(export_response.content)) as archive:
        assert "manifest.json" in archive.namelist()
        assert "summary.csv" in archive.namelist()

    import_response = client.post(
        "/api/experiments/import/package",
        files={"file": ("exported.zip", export_response.content, "application/zip")},
        data={"name": "", "description": ""},
    )
    assert import_response.status_code == 201, import_response.text
    payload = import_response.json()
    assert payload["source"] == "imported_package"
    assert payload["status"] == "completed"
    assert payload["runtime_config_available"] is False
    assert payload["log_available"] is False


def test_import_package_api_rejects_invalid_zip(isolated_manager) -> None:
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/experiments/import/package",
        files={"file": ("bad.zip", b"not a zip", "application/zip")},
        data={"name": "", "description": ""},
    )
    assert response.status_code == 422
    assert "errors" in response.json()["detail"]
