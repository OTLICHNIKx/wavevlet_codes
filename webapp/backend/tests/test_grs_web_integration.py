from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.models.config import ResearchConfigSchema
from app.services.config_adapter import builtin_presets, schema_to_research


def grs_document() -> dict:
    return {
        "message_count": 8,
        "message_seed": 12345,
        "noise_seed": 54321,
        "ebn0_db_values": [2.0],
        "codes": [{
            "name": "reed_solomon_binary_16_8",
            "family": "reed_solomon_binary",
            "n": 16,
            "k": 8,
            "reed_solomon_m": 4,
            "reed_solomon_symbol_n": 4,
            "reed_solomon_symbol_k": 2,
            "reed_solomon_primitive_polynomial": 19,
            "reed_solomon_evaluation_points": [0, 1, 2, 3],
            "reed_solomon_column_multipliers": [1, 3, 1, 3],
            "syndrome_max_error_weight": 2,
        }],
        "decoders": {
            "run_syndrome": True, "run_hard_mld": False,
            "run_soft_mld": False, "run_chase": False,
            "syndrome_max_error_weight": 2,
            "chase_inner_decoder_max_error_weight": 2,
            "chase_unreliable_positions_count": 4,
            "max_k_for_mld": 16,
        },
        "results_dir": "research_results/test_grs",
    }


def test_backend_accepts_and_round_trips_grs_parameters() -> None:
    schema = ResearchConfigSchema.model_validate(grs_document())
    research = schema_to_research(schema)
    code = research.codes[0]
    assert code.family == "reed_solomon_binary"
    assert code.reed_solomon_evaluation_points == (0, 1, 2, 3)
    assert code.reed_solomon_column_multipliers == (1, 3, 1, 3)
    restored = ResearchConfigSchema.model_validate(research.to_json_dict())
    restored_code = restored.codes[0]
    assert restored_code.reed_solomon_evaluation_points == [0, 1, 2, 3]
    assert restored_code.reed_solomon_column_multipliers == [1, 3, 1, 3]


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("reed_solomon_column_multipliers", [1, 3, 0, 3], "ненулевыми"),
        ("reed_solomon_evaluation_points", [0, 1, 1, 3], "уникальны"),
    ],
)
def test_backend_rejects_invalid_grs_points_and_multipliers(field, value, fragment) -> None:
    document = deepcopy(grs_document())
    document["codes"][0][field] = value
    with pytest.raises(ValidationError, match=fragment):
        ResearchConfigSchema.model_validate(document)


def test_web_backend_exposes_grs_presets_for_all_three_sizes() -> None:
    presets = {entry["id"]: entry["config"] for entry in builtin_presets()["codes"]}
    assert {"GRS_BINARY_16_8", "GRS_BINARY_32_16", "GRS_BINARY_64_32"} <= set(presets)
    grs16 = presets["GRS_BINARY_16_8"]
    assert grs16["family"] == "reed_solomon_binary"
    assert grs16["reed_solomon_evaluation_points"] == [0, 1, 2, 3]
    assert grs16["reed_solomon_column_multipliers"] == [1, 3, 1, 3]


def test_web_backend_exposes_four_family_20k_experiment_presets() -> None:
    presets = {entry["id"]: entry["config"] for entry in builtin_presets()["experiments"]}
    assert {"FOUR_FAMILIES_20K_16_8", "FOUR_FAMILIES_20K_32_16", "FOUR_FAMILIES_20K_64_32"} <= set(presets)
    assert presets["FOUR_FAMILIES_20K_32_16"]["message_count"] == 20_000
    assert presets["FOUR_FAMILIES_20K_64_32"]["decoders"]["syndrome_max_error_weight"] == 3
