from dataclasses import replace

import pytest

from research.config import (
    FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
    FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
    FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
)
from research.runner import run_research


ALL_DECODERS = {"syndrome", "chase", "hard_mld", "soft_mld"}

CONFIGS = (
    FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
    FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
    FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
)


@pytest.mark.parametrize("config", CONFIGS)
def test_five_family_full_decoder_presets_enable_every_decoder(
    config,
) -> None:
    assert config.message_count == 20_000
    assert {
        config.decoders.run_syndrome,
        config.decoders.run_chase,
        config.decoders.run_hard_mld,
        config.decoders.run_soft_mld,
    } == {True}
    assert config.decoders.max_k_for_mld == 16
    assert len(config.codes) == 5


@pytest.mark.parametrize("config", CONFIGS)
def test_five_family_smoke_rows_follow_mld_limit(config, tmp_path) -> None:
    smoke = replace(
        config,
        message_count=2,
        ebn0_db_values=(2.0,),
        results_dir=str(tmp_path / "five_family_full_decoder"),
    )
    rows = run_research(smoke)
    assert len(rows) == 20
    assert {row["decoder"] for row in rows} == ALL_DECODERS
    mld_rows = [
        row for row in rows if row["decoder"] in {"hard_mld", "soft_mld"}
    ]
    if smoke.codes[0].k <= smoke.decoders.max_k_for_mld:
        assert all(not row["skipped"] for row in mld_rows)
    else:
        assert all(row["skipped"] for row in mld_rows)
        assert all("k = 32" in row["skip_reason"] for row in mld_rows)
    non_mld_rows = [
        row for row in rows if row["decoder"] in {"syndrome", "chase"}
    ]
    assert all(not row["skipped"] for row in non_mld_rows)
    ldpc_rows = [row for row in rows if row["code_family"] == "ldpc"]
    assert len(ldpc_rows) == 4
    assert {row["code_name"] for row in ldpc_rows} == {
        config.codes[4].name
    }
