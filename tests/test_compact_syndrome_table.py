import numpy as np

from decode.syndrome_decoding import (
    build_compact_syndrome_table,
    build_syndrome_table,
    syndrome_decode,
)


def test_compact_table_matches_legacy_table() -> None:
    parity_check_matrix = np.array(
        [
            [1, 1, 0],
            [0, 1, 1],
        ],
        dtype=np.uint8,
    )

    legacy = build_syndrome_table(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=1,
    )

    compact = build_compact_syndrome_table(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=1,
    )

    assert compact.pattern_count == 4
    assert compact.entry_count == len(legacy)
    assert compact.collision_count == 0

    for syndrome, error_vector in legacy.items():
        assert np.array_equal(
            compact[syndrome],
            error_vector,
        )


def test_compact_table_counts_collisions() -> None:
    parity_check_matrix = np.array(
        [[1, 1]],
        dtype=np.uint8,
    )

    compact = build_compact_syndrome_table(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=1,
    )

    assert compact.pattern_count == 3
    assert compact.entry_count == 2
    assert compact.collision_count == 1

    assert np.array_equal(
        compact[(1,)],
        np.array([1, 0], dtype=np.uint8),
    )


def test_syndrome_decode_accepts_compact_table() -> None:
    parity_check_matrix = np.array(
        [
            [1, 1, 0],
            [0, 1, 1],
        ],
        dtype=np.uint8,
    )

    received_word = np.array(
        [1, 0, 0],
        dtype=np.uint8,
    )

    legacy = build_syndrome_table(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=1,
    )

    compact = build_compact_syndrome_table(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=1,
    )

    legacy_result = syndrome_decode(
        received_word=received_word,
        parity_check_matrix=parity_check_matrix,
        syndrome_table=legacy,
        max_error_weight=1,
    )

    compact_result = syndrome_decode(
        received_word=received_word,
        parity_check_matrix=parity_check_matrix,
        syndrome_table=compact,
        max_error_weight=1,
    )

    assert compact_result.success
    assert legacy_result.success
    assert np.array_equal(
        compact_result.corrected_word,
        legacy_result.corrected_word,
    )
    assert np.array_equal(
        compact_result.error_vector,
        legacy_result.error_vector,
    )
