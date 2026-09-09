from dataclasses import replace

from research.config import (
    EQUAL_DECODER_20K_FOUR_FAMILIES_32_16,
    EQUAL_DECODER_20K_FOUR_FAMILIES_64_32,
    FOUR_FAMILIES_SMOKE_CONFIG,
)
from research.runner import run_research


def test_32_16_is_equal_nkr_equal_decoder_not_equal_distance() -> None:
    config = EQUAL_DECODER_20K_FOUR_FAMILIES_32_16
    assert {(code.n, code.k) for code in config.codes} == {(32, 16)}
    assert {code.k / code.n for code in config.codes} == {0.5}
    assert {code.syndrome_max_error_weight for code in config.codes} == {2}
    # wavelet, bch_derived (optimized puncture (20,22)), goppa
    # (phase-2 message-functional kernel, d 7 -> 8), reed_solomon
    # (optimized multipliers, d 6 -> 7)
    assert [code.minimum_distance_exact for code in config.codes] == [8, 6, 8, 7]


def test_64_32_uses_common_t3_and_correct_distance_metadata() -> None:
    config = EQUAL_DECODER_20K_FOUR_FAMILIES_64_32
    assert {(code.n, code.k) for code in config.codes} == {(64, 32)}
    assert {code.k / code.n for code in config.codes} == {0.5}
    assert config.decoders.syndrome_max_error_weight == 3
    assert {code.syndrome_max_error_weight for code in config.codes} == {3}
    # wavelet optimized (certificate 11 <= d <= 14), bch_derived
    # (9..10), goppa (9), reed_solomon (10)
    assert [
        (
            code.minimum_distance_exact,
            code.minimum_distance_lower_bound,
            code.minimum_distance_upper_bound,
        )
        for code in config.codes
    ] == [
        (None, 11, 14),
        (None, 9, 10),
        (9, 9, 9),
        (10, 10, 10),
    ]


def test_summary_rows_preserve_distance_upper_bound_and_evidence(tmp_path) -> None:
    config = replace(
        EQUAL_DECODER_20K_FOUR_FAMILIES_32_16,
        message_count=4, ebn0_db_values=(2.0,),
        results_dir=str(tmp_path / "summary"),
    )
    rows = run_research(config)
    assert rows
    assert all("minimum_distance_upper_bound" in row for row in rows)
    assert all("distance_evidence" in row for row in rows)
    assert all(row["distance_evidence"] for row in rows)
