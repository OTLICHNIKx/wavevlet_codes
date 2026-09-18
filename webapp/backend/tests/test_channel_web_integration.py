from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.config import ResearchConfigSchema
from app.services.config_adapter import (
    builtin_presets,
    schema_to_research,
    validate_schema,
)
from research.runner import run_research


def experiment_by_id(preset_id: str) -> dict:
    experiments = {
        entry["id"]: entry["config"]
        for entry in builtin_presets()["experiments"]
    }
    assert preset_id in experiments, sorted(experiments)
    return experiments[preset_id]


def test_backend_exposes_new_channel_presets() -> None:
    ids = {entry["id"] for entry in builtin_presets()["experiments"]}
    assert {
        "NEW_CHANNELS_RAYLEIGH",
        "NEW_CHANNELS_SINUSOIDAL",
        "NEW_CHANNELS_RAYLEIGH_AWGN",
        "NEW_CHANNELS_AWGN_BASELINE",
    } <= ids
    ray = experiment_by_id("NEW_CHANNELS_RAYLEIGH")
    assert ray["channel_type"] == "rayleigh"
    assert [code["family"] for code in ray["codes"]] == [
        "wavelet", "bch_derived", "goppa_derived", "reed_solomon_binary",
        "ldpc",
    ]
    assert ray["message_count"] == 100
    assert ray["ebn0_db_values"] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    sinus = experiment_by_id("NEW_CHANNELS_SINUSOIDAL")
    assert sinus["channel_params"] == {
        "amplitude": 0.5, "frequency": 0.125, "phase": 0.0,
    }


def test_schema_accepts_and_defaults_channel() -> None:
    ray = experiment_by_id("NEW_CHANNELS_RAYLEIGH")
    research = schema_to_research(ResearchConfigSchema.model_validate(ray))
    assert research.channel_type == "rayleigh"
    legacy = deepcopy(ray)
    legacy.pop("channel_type")
    legacy.pop("channel_params")
    research_legacy = schema_to_research(
        ResearchConfigSchema.model_validate(legacy)
    )
    assert research_legacy.channel_type == "awgn"


def test_schema_rejects_unknown_channel() -> None:
    ray = experiment_by_id("NEW_CHANNELS_RAYLEIGH")
    bad = deepcopy(ray)
    bad["channel_type"] = "quantum"
    with pytest.raises(ValidationError):
        ResearchConfigSchema.model_validate(bad)


def test_validate_schema_passes_rayleigh_config() -> None:
    ray = experiment_by_id("NEW_CHANNELS_RAYLEIGH")
    response = validate_schema(ResearchConfigSchema.model_validate(ray))
    assert response.valid, response.errors


def test_backend_run_with_sinusoidal_channel(tmp_path) -> None:
    sinus = deepcopy(experiment_by_id("NEW_CHANNELS_SINUSOIDAL"))
    sinus["message_count"] = 4
    sinus["ebn0_db_values"] = [3.0]
    sinus["decoders"] = dict(
        sinus["decoders"], run_hard_mld=False, run_soft_mld=False
    )
    config = schema_to_research(
        ResearchConfigSchema.model_validate(sinus),
        results_dir=str(tmp_path / "sinus"),
    )
    rows = run_research(config)
    assert rows
    assert all(0.0 <= row["ber"] <= 1.0 for row in rows if not row["skipped"])


def test_realistic_sinusoidal_preset_exposed() -> None:
    preset = experiment_by_id("REALISTIC_SINUSOIDAL_TEST")
    assert preset["channel_type"] == "sinusoidal"
    assert preset["channel_params"]["mode"] == "realistic"
    assert preset["channel_params"]["num_interferers"] == 3
    research = schema_to_research(ResearchConfigSchema.model_validate(preset))
    assert research.channel_params["mode"] == "realistic"
    response = validate_schema(ResearchConfigSchema.model_validate(preset))
    assert response.valid, response.errors


def test_frontend_sources_expose_channel_options() -> None:
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    types = (frontend / "src" / "types.ts").read_text(encoding="utf-8")
    assert "ChannelType" in types
    assert '"rayleigh_awgn"' in types
    assert "channel_params?: ChannelParams" in types
    assert "num_interferers" in types
    page = (
        frontend / "src" / "pages" / "NewExperimentPage.tsx"
    ).read_text(encoding="utf-8")
    assert "Канал" in page
    for option in ("awgn", "rayleigh", "sinusoidal", "rayleigh_awgn"):
        assert f'value="{option}"' in page
    assert "Реалистичная" in page
    dist_index = (frontend / "dist" / "index.html").read_text(encoding="utf-8")
    assert "assets" in dist_index  # собранный бандл обновлён
    bundled = "".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (frontend / "dist" / "assets").glob("index-*.js")
    )
    assert "rayleigh_awgn" in bundled  # опция канала попала в собранный UI
    assert "realistic" in bundled  # режим реалистичной помехи собран
