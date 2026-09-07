import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import configs
from app.db import database
from app.models.experiment import Base, CustomPreset, Experiment, ExperimentStatus


@pytest.fixture()
def preset_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'presets.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(configs, "SessionLocal", sessions)

    from app.main import app

    return TestClient(app), sessions


def _payload(name: str = "Custom 500") -> dict:
    return {
        "name": name,
        "description": "Three-family preset",
        "config": {
            "message_count": 500,
            "message_seed": 12345,
            "noise_seed": 54321,
            "ebn0_db_values": [0.0, 3.0, 5.0],
            "codes": [
                {
                    "name": "goppa_derived_32_16",
                    "family": "goppa_derived",
                    "n": 32,
                    "k": 16,
                    "goppa_m": 5,
                    "goppa_degree": 3,
                    "goppa_support_size": 32,
                    "syndrome_max_error_weight": 2,
                    "chase_inner_decoder_max_error_weight": 2,
                    "chase_unreliable_positions_count": 6,
                }
            ],
            "decoders": {
                "run_syndrome": True,
                "run_hard_mld": False,
                "run_soft_mld": False,
                "run_chase": True,
                "syndrome_max_error_weight": 2,
                "chase_inner_decoder_max_error_weight": 2,
                "chase_unreliable_positions_count": 6,
                "max_k_for_mld": 16,
            },
            "results_dir": "",
        },
    }


def test_custom_preset_crud_duplicate_and_persistence(preset_client) -> None:
    client, sessions = preset_client

    created_response = client.post("/api/presets", json=_payload())
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()
    assert created["description"] == "Three-family preset"
    assert created["schema_version"] == 1

    loaded = client.get(f"/api/presets/{created['id']}")
    assert loaded.status_code == 200
    assert loaded.json()["config"]["message_count"] == 500

    updated_payload = _payload("Custom updated")
    updated_payload["description"] = "Updated"
    updated_payload["config"]["message_count"] = 250
    updated = client.put(f"/api/presets/{created['id']}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Custom updated"
    assert updated.json()["config"]["message_count"] == 250

    duplicated = client.post(f"/api/presets/{created['id']}/duplicate")
    assert duplicated.status_code == 201
    duplicate = duplicated.json()
    assert duplicate["id"] != created["id"]
    assert duplicate["config"] == updated.json()["config"]

    presets = client.get("/api/presets").json()
    assert len(presets["user"]) == 2
    assert len(presets["experiments"]) > 0
    assert len(presets["codes"]) > 0

    with sessions() as session:
        persisted = session.get(CustomPreset, created["id"])
        assert persisted is not None
        assert json.loads(persisted.config_json)["message_count"] == 250

    deleted = client.delete(f"/api/presets/{created['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/presets/{created['id']}").status_code == 404
    assert client.get(f"/api/presets/{duplicate['id']}").status_code == 200


def test_invalid_custom_preset_is_rejected_without_db_record(preset_client) -> None:
    client, sessions = preset_client
    payload = _payload()
    payload["config"]["codes"][0]["k"] = 33

    response = client.post("/api/presets", json=payload)

    assert response.status_code == 422
    with sessions() as session:
        assert session.query(CustomPreset).count() == 0


def test_deleting_preset_does_not_delete_experiment_snapshot(preset_client) -> None:
    client, sessions = preset_client
    created = client.post("/api/presets", json=_payload()).json()

    with sessions() as session:
        session.add(
            Experiment(
                id="snapshot-experiment",
                name="Completed from preset",
                description="",
                status=ExperimentStatus.completed,
                config_json=json.dumps(created["config"]),
                results_dir="unused",
                log_path="",
            )
        )
        session.commit()

    assert client.delete(f"/api/presets/{created['id']}").status_code == 200

    with sessions() as session:
        snapshot = session.get(Experiment, "snapshot-experiment")
        assert snapshot is not None
        assert json.loads(snapshot.config_json) == created["config"]


def test_legacy_json_preset_migration_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'migration.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    (presets_dir / "legacy.json").write_text(
        json.dumps({"name": "Legacy", "config": _payload()["config"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(database, "SessionLocal", sessions)
    monkeypatch.setattr(database, "PRESETS_DIR", presets_dir)

    database._migrate_legacy_presets()
    database._migrate_legacy_presets()

    with sessions() as session:
        records = session.query(CustomPreset).all()
        assert len(records) == 1
        assert records[0].name == "Legacy"
