from dataclasses import replace

import numpy as np
import pytest

from research.code_factory import build_code_from_config
from research.config import (
    FOUR_FAMILIES_SMOKE_CONFIG,
    EQUAL_DECODER_20K_FOUR_FAMILIES_16_8,
    EQUAL_DECODER_20K_FOUR_FAMILIES_32_16,
    EQUAL_DECODER_20K_FOUR_FAMILIES_64_32,
)
from research.dataset import build_all_datasets
from research.runner import run_research


EXPECTED_FAMILIES = ("wavelet", "bch_derived", "goppa_derived", "reed_solomon_binary")


def _exact_distance(code) -> int:
    values = np.arange(1, 1 << code.k, dtype=np.uint64)[:, None]
    messages = ((values >> np.arange(code.k, dtype=np.uint64)[None, :]) & 1).astype(np.uint8)
    return int(np.sum((messages @ code.generator_matrix) % 2, axis=1).min())


def test_four_families_16_8_have_equal_actual_distance_and_fair_config() -> None:
    config = FOUR_FAMILIES_SMOKE_CONFIG
    assert tuple(code.family for code in config.codes) == EXPECTED_FAMILIES
    assert {(code.n, code.k) for code in config.codes} == {(16, 8)}
    assert {code.k / code.n for code in config.codes} == {0.5}
    assert {code.syndrome_max_error_weight for code in config.codes} == {config.decoders.syndrome_max_error_weight}
    assert config.decoders.syndrome_max_error_weight == 2
    codes = [build_code_from_config(code_config) for code_config in config.codes]
    assert {_exact_distance(code) for code in codes} == {5}

    datasets = build_all_datasets(config.message_count, config.codes, config.message_seed, config.noise_seed)
    values = [datasets[code.name] for code in config.codes]
    for dataset in values[1:]:
        assert dataset.messages is values[0].messages
        assert dataset.base_noise is values[0].base_noise
        assert np.array_equal(dataset.messages, values[0].messages)
        assert np.array_equal(dataset.base_noise, values[0].base_noise)


def test_four_family_16_8_smoke_produces_only_generic_syndrome_rows(tmp_path) -> None:
    config = replace(FOUR_FAMILIES_SMOKE_CONFIG, results_dir=str(tmp_path / "smoke"), ebn0_db_values=(2.0,))
    rows = run_research(config)
    assert len(rows) == 4
    assert {row["code_family"] for row in rows} == set(EXPECTED_FAMILIES)
    assert {row["decoder"] for row in rows} == {"syndrome"}
    assert {row["message_count"] for row in rows} == {config.message_count}
    assert all(not row["skipped"] for row in rows)


@pytest.mark.parametrize(
    "config",
    [
        EQUAL_DECODER_20K_FOUR_FAMILIES_16_8,
        EQUAL_DECODER_20K_FOUR_FAMILIES_32_16,
        EQUAL_DECODER_20K_FOUR_FAMILIES_64_32,
    ],
)
def test_all_size_four_family_configs_have_shared_data_and_small_pipeline_run(config, tmp_path) -> None:
    assert tuple(code.family for code in config.codes) == EXPECTED_FAMILIES
    assert len({(code.n, code.k) for code in config.codes}) == 1
    assert {code.k / code.n for code in config.codes} == {0.5}
    assert {code.syndrome_max_error_weight for code in config.codes} == {config.decoders.syndrome_max_error_weight}
    datasets = build_all_datasets(8, config.codes, config.message_seed, config.noise_seed)
    values = [datasets[code.name] for code in config.codes]
    assert all(dataset.messages.shape == (8, config.codes[0].k) for dataset in values)
    assert all(dataset.base_noise.shape == (8, config.codes[0].n) for dataset in values)
    assert all(dataset.messages is values[0].messages for dataset in values)
    assert all(dataset.base_noise is values[0].base_noise for dataset in values)
    rows = run_research(replace(config, message_count=8, ebn0_db_values=(2.0,), results_dir=str(tmp_path / config.results_dir.replace("/", "_"))))
    assert len(rows) == 4
    assert {row["code_family"] for row in rows} == set(EXPECTED_FAMILIES)
    assert {row["message_count"] for row in rows} == {8}
    assert all(not row["skipped"] for row in rows)
