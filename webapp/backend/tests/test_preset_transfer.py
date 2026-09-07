import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import configs, experiments
from app.models.experiment import Base, CustomPreset, Experiment, ExperimentStatus
from app.models.config import ResearchConfigSchema
from app.services import custom_presets, experiment_manager
from app.services.preset_io import (
    PRESET_FORMAT,
    PRESET_SCHEMA_VERSION,
    PresetValidationError,
    build_preset_document,
    encode_preset_document,
    parse_and_validate_preset,
)


def _config() -> dict:
    return {
        "message_count": 50,
        "message_seed": 12345,
        "noise_seed": 54321,
        "ebn0_db_values": [2.0],
        "codes": [{
            "name": "goppa_derived_16_8",
            "family": "goppa_derived",
            "n": 16,
            "k": 8,
            "goppa_m": 4,
            "goppa_degree": 2,
            "goppa_support_size": 16,
            "syndrome_max_error_weight": 1,
            "chase_inner_decoder_max_error_weight": 1,
            "chase_unreliable_positions_count": 4,
        }],
        "decoders": {
            "run_syndrome": True,
            "run_hard_mld": False,
            "run_soft_mld": False,
            "run_chase": True,
            "syndrome_max_error_weight": 1,
            "chase_inner_decoder_max_error_weight": 1,
            "chase_unreliable_positions_count": 4,
            "max_k_for_mld": 16,
        },
        "results_dir": "",
    }


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'presets.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(configs, "SessionLocal", sessions)
    monkeypatch.setattr(experiments, "SessionLocal", sessions)
    monkeypatch.setattr(custom_presets, "SessionLocal", sessions)
    monkeypatch.setattr(experiment_manager, "SessionLocal", sessions)
    monkeypatch.setattr(experiments, "resolve_results_dir", lambda path: Path(path))
    monkeypatch.setattr(experiment_manager, "resolve_results_dir", lambda path: Path(path))

    from app.main import app

    return TestClient(app), sessions, tmp_path


def test_preset_json_export_import_round_trip(api_client) -> None:
    client, _, _ = api_client
    create = client.post(
        "/api/presets",
        json={"name": "Portable", "description": "Round trip", "config": _config()},
    )
    assert create.status_code == 201, create.text
    original = create.json()

    exported = client.get(f"/api/presets/{original['id']}/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/json"
    document = json.loads(exported.content)
    assert document["schema_version"] == PRESET_SCHEMA_VERSION
    assert document["format"] == PRESET_FORMAT
    assert "id" not in document
    assert "created_at" not in document

    imported = client.post(
        "/api/presets/import",
        files={"file": ("portable.preset.json", exported.content, "application/json")},
    )
    assert imported.status_code == 201, imported.text
    copy = imported.json()
    assert copy["id"] != original["id"]
    assert copy["name"] == original["name"]
    assert copy["description"] == original["description"]
    assert copy["config"] == original["config"]


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"schema_version": 999, "format": PRESET_FORMAT, "name": "x", "config": {}},
        {"schema_version": 1, "format": "wrong", "name": "x", "config": {}},
        {"schema_version": 1, "format": PRESET_FORMAT, "name": "", "config": {}},
    ],
)
def test_invalid_preset_document_is_rejected(document: dict) -> None:
    with pytest.raises(PresetValidationError):
        parse_and_validate_preset(json.dumps(document).encode("utf-8"))


def test_clone_completed_experiment_as_preset(api_client) -> None:
    client, sessions, tmp_path = api_client
    results_dir = tmp_path / "result"
    results_dir.mkdir()
    (results_dir / "runtime_config.json").write_text(json.dumps(_config()), encoding="utf-8")
    with sessions() as session:
        session.add(Experiment(
            id="completed-with-config",
            name="Completed run",
            description="Original description",
            status=ExperimentStatus.completed,
            config_json=json.dumps(_config()),
            results_dir=str(results_dir),
            log_path="",
        ))
        session.commit()

    response = client.post("/api/experiments/completed-with-config/clone-preset")
    assert response.status_code == 201, response.text
    preset = response.json()
    assert preset["name"] == "Completed run (preset)"
    assert preset["description"] == "Original description"
    assert preset["config"] == ResearchConfigSchema.model_validate(_config()).model_dump()
    assert preset["config"]["results_dir"] == ""

    with sessions() as session:
        assert session.get(CustomPreset, preset["id"]) is not None


def test_csv_only_experiment_cannot_be_cloned_as_preset(api_client) -> None:
    client, sessions, tmp_path = api_client
    results_dir = tmp_path / "csv-only"
    results_dir.mkdir()
    with sessions() as session:
        session.add(Experiment(
            id="csv-only",
            name="CSV only",
            description="",
            status=ExperimentStatus.completed,
            config_json=json.dumps(_config()),
            results_dir=str(results_dir),
            log_path="",
        ))
        session.commit()

    response = client.post("/api/experiments/csv-only/clone-preset")
    assert response.status_code == 409
    assert response.json()["detail"] == "Runtime configuration unavailable"


def test_preset_document_contains_only_config_data() -> None:
    document = build_preset_document(
        name="Portable",
        description="",
        config=_config(),
    )
    parsed = parse_and_validate_preset(encode_preset_document(document))
    assert parsed.config.model_dump()["message_count"] == 50
