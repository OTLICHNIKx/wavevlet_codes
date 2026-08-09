from dataclasses import replace

import numpy as np

from research import runner
from research.config import DecoderResearchConfig, WAVELET_16_8_CONFIG


def test_equal_syndrome_and_chase_t_build_one_table(monkeypatch) -> None:
    calls: list[int] = []

    def fake_build_compact_syndrome_table(*, parity_check_matrix, max_error_weight):
        calls.append(max_error_weight)
        return object()

    monkeypatch.setattr(
        runner,
        "build_compact_syndrome_table",
        fake_build_compact_syndrome_table,
    )

    code_config = replace(
        WAVELET_16_8_CONFIG,
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=2,
    )
    decoder_config = DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=False,
        run_soft_mld=False,
        run_chase=True,
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=2,
        chase_unreliable_positions_count=4,
        max_k_for_mld=16,
    )

    tables, build_times = runner.build_syndrome_table_cache(
        parity_check_matrix=np.zeros((8, 16), dtype=np.uint8),
        code_config=code_config,
        decoder_config=decoder_config,
    )

    assert calls == [2]
    assert set(tables) == {2}
    assert set(build_times) == {2}


def test_different_syndrome_and_chase_t_build_two_tables(monkeypatch) -> None:
    calls: list[int] = []

    def fake_build_compact_syndrome_table(*, parity_check_matrix, max_error_weight):
        calls.append(max_error_weight)
        return object()

    monkeypatch.setattr(
        runner,
        "build_compact_syndrome_table",
        fake_build_compact_syndrome_table,
    )

    code_config = replace(
        WAVELET_16_8_CONFIG,
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=3,
    )
    decoder_config = DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=False,
        run_soft_mld=False,
        run_chase=True,
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=3,
        chase_unreliable_positions_count=4,
        max_k_for_mld=16,
    )

    tables, _ = runner.build_syndrome_table_cache(
        parity_check_matrix=np.zeros((8, 16), dtype=np.uint8),
        code_config=code_config,
        decoder_config=decoder_config,
    )

    assert calls == [2, 3]
    assert set(tables) == {2, 3}
