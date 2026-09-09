from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.models.config import ResearchConfigSchema
from app.services.code_metadata import build_code_metadata_list
from app.services.config_adapter import builtin_presets, schema_to_research


def ldpc_document() -> dict:
    return {
        "message_count": 8,
        "message_seed": 12345,
        "noise_seed": 54321,
        "ebn0_db_values": [2.0],
        "codes": [{
            "name": "ldpc_16_8",
            "family": "ldpc",
            "n": 16,
            "k": 8,
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
        "results_dir": "research_results/test_ldpc",
    }


def test_backend_accepts_ldpc_family_and_round_trips() -> None:
    schema = ResearchConfigSchema.model_validate(ldpc_document())
    research = schema_to_research(schema)
    code = research.codes[0]
    assert code.family == "ldpc"
    assert (code.n, code.k) == (16, 8)
    restored = ResearchConfigSchema.model_validate(research.to_json_dict())
    assert restored.codes[0].family == "ldpc"


def test_backend_rejects_unknown_ldpc_dimensions() -> None:
    document = deepcopy(ldpc_document())
    document["codes"][0].update({"name": "ldpc_20_10", "n": 20, "k": 10})
    with pytest.raises(ValidationError, match="ldpc"):
        ResearchConfigSchema.model_validate(document)


def test_web_backend_exposes_ldpc_presets_for_all_three_sizes() -> None:
    presets = {entry["id"]: entry["config"] for entry in builtin_presets()["codes"]}
    assert {"LDPC_16_8_CONFIG", "LDPC_32_16_CONFIG", "LDPC_64_32_CONFIG"} <= set(presets)
    ldpc16 = presets["LDPC_16_8_CONFIG"]
    assert ldpc16["family"] == "ldpc"
    assert ldpc16["minimum_distance_exact"] == 5


def test_web_backend_exposes_five_family_20k_experiment_presets() -> None:
    presets = {
        entry["id"]: entry["config"]
        for entry in builtin_presets()["experiments"]
    }
    assert {
        "FIVE_FAMILIES_20K_16_8",
        "FIVE_FAMILIES_20K_32_16",
        "FIVE_FAMILIES_20K_64_32",
    } <= set(presets)
    families = [code["family"] for code in presets["FIVE_FAMILIES_20K_16_8"]["codes"]]
    assert families == [
        "wavelet",
        "bch_derived",
        "goppa_derived",
        "reed_solomon_binary",
        "ldpc",
    ]
    assert presets["FIVE_FAMILIES_20K_64_32"]["decoders"]["syndrome_max_error_weight"] == 3


def test_code_metadata_enriches_ldpc_preset_with_weight_profile() -> None:
    metadata = build_code_metadata_list([
        {"name": "ldpc_64_32", "family": "ldpc", "n": 64, "k": 32},
    ])
    entry = metadata[0]
    assert entry["ldpc_h_max_row_weight"] <= 8
    assert entry["ldpc_h_min_column_weight"] >= 2
    assert entry["ldpc_h_density"] < 0.2
