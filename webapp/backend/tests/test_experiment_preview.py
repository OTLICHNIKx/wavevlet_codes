from copy import deepcopy

from fastapi.testclient import TestClient

from app.models.config import ResearchConfigSchema
from app.services.experiment_preview import build_experiment_preview
from app.services.config_adapter import builtin_presets


def _config(*code_names: str) -> ResearchConfigSchema:
    builtins = builtin_presets()
    by_name = {
        item["config"]["name"]: item["config"]
        for item in builtins["codes"]
    }
    codes = [deepcopy(by_name[name]) for name in code_names]
    return ResearchConfigSchema.model_validate(
        {
            "message_count": 500,
            "message_seed": 12345,
            "noise_seed": 54321,
            "ebn0_db_values": [0.0, 3.0, 5.0],
            "codes": codes,
            "decoders": {
                "run_syndrome": True,
                "run_hard_mld": True,
                "run_soft_mld": True,
                "run_chase": True,
                "syndrome_max_error_weight": 2,
                "chase_inner_decoder_max_error_weight": 2,
                "chase_unreliable_positions_count": 6,
                "max_k_for_mld": 16,
            },
        }
    )


def test_preview_equal_three_family_group() -> None:
    config = _config(
        "wavelet_32_16",
        "bch_derived_32_16",
        "goppa_derived_32_16",
    )
    for code in config.codes:
        code.syndrome_max_error_weight = 2
        code.chase_inner_decoder_max_error_weight = 2
        code.chase_unreliable_positions_count = 6
    result = build_experiment_preview(config)

    assert result["valid"] is True
    assert result["warnings"] == []
    assert result["summary"]["code_count"] == 3
    assert result["common_random_numbers"]["enabled"] is True
    assert result["groups"][0]["rate_matched"] is True
    assert result["groups"][0]["decoder_matched"] is True
    assert result["workload"]["code_snr_points"] == 9


def test_preview_warns_about_rate_and_decoder_mismatch() -> None:
    config = _config("wavelet_16_8", "goppa_derived_16_8")
    config.codes[1].k = 6
    config.codes[1].syndrome_max_error_weight = 1
    config.codes[1].chase_unreliable_positions_count = 8

    result = build_experiment_preview(config)

    assert result["valid"] is False
    assert any("Rate mismatch" in warning for warning in result["warnings"])
    assert any("Decoder parameters are not equal" in warning for warning in result["warnings"])


def test_preview_reports_mld_skipped_for_k_above_limit() -> None:
    result = build_experiment_preview(_config("goppa_derived_64_32"))

    assert result["valid"] is True
    report = result["groups"][0]["codes"][0]
    assert report["hard_mld"]["status"] == "skipped"
    assert report["soft_mld"]["status"] == "skipped"
    assert "max_k_for_mld" in report["hard_mld"]["reason"]


def test_preview_warns_when_syndrome_exceeds_known_radius() -> None:
    config = _config("goppa_derived_16_8")
    config.codes[0].syndrome_max_error_weight = 3

    result = build_experiment_preview(config)

    assert any("exceeds known guaranteed radius" in warning for warning in result["warnings"])


def test_preview_invalid_configuration_has_errors_and_no_groups() -> None:
    config = _config("goppa_derived_32_16")
    config.codes[0].n = 16

    result = build_experiment_preview(config)

    assert result["valid"] is False
    assert result["errors"]
    assert result["groups"] == []


def test_preview_api_returns_backend_report() -> None:
    from app.main import app

    config = _config("goppa_derived_64_32")
    response = TestClient(app).post(
        "/api/configs/preview",
        json=config.model_dump(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["groups"][0]["codes"][0]["hard_mld"]["status"] == "skipped"
    assert payload["common_random_numbers"]["enabled"] is True
