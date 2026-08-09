import numpy as np
import pytest

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


def test_compact_table_rejects_invalid_max_error_weight() -> None:
    equal_matrix = np.array(
        [[1, 0], [0, 1]],
        dtype=np.uint8,
    )

    with pytest.raises(TypeError, match="целым числом"):
        build_compact_syndrome_table(
            parity_check_matrix=equal_matrix,
            max_error_weight=1.5,
        )

    with pytest.raises(ValueError, match="неотрицательным"):
        build_compact_syndrome_table(
            parity_check_matrix=equal_matrix,
            max_error_weight=-1,
        )

    with pytest.raises(ValueError, match="не может быть больше длины слова"):
        build_compact_syndrome_table(
            parity_check_matrix=equal_matrix,
            max_error_weight=3,
        )


def test_compact_table_mapping_interface() -> None:
    parity_check_matrix = np.array(
        [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.uint8,
    )

    compact = build_compact_syndrome_table(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=1,
    )

    # __len__
    assert len(compact) == 4  # weight 0 + 3 errors of weight 1

    # __iter__
    syndromes = set(compact)
    assert len(syndromes) == 4

    # __contains__ (через get-item)
    assert (0, 0, 0) in compact
    assert (1, 0, 0) in compact
    assert (1, 1, 1) not in compact

    # Invalid syndrome length
    with pytest.raises(KeyError):
        compact[(1, 0)]

    # Invalid syndrome value (не 0 и не 1)
    with pytest.raises(KeyError):
        compact[(2, 0, 0)]

    # .get возвращает ndarray
    error_vector = compact.get((1, 0, 0))
    assert isinstance(error_vector, np.ndarray)
    assert np.array_equal(
        error_vector,
        np.array([1, 0, 0], dtype=np.uint8),
    )


def test_compact_table_wavelet_64_32_t3() -> None:
    """Performance/regression: compact table for Wavelet [64,32], t=3."""
    from research.code_factory import build_code_from_config
    from research.config import WAVELET_64_32_CONFIG

    from time import perf_counter

    code = build_code_from_config(WAVELET_64_32_CONFIG)
    start = perf_counter()

    compact = build_compact_syndrome_table(
        parity_check_matrix=code.parity_check_matrix,
        max_error_weight=3,
    )
    elapsed = perf_counter() - start

    assert compact.pattern_count == 43745
    assert compact.entry_count == 43745
    assert compact.collision_count == 0

    # Sanity check: не должно быть медленных
    assert elapsed < 5.0


def test_compact_table_bch_derived_64_32_t4() -> None:
    """Performance/regression: compact table for BCH-derived [64,32], t=4.

    Проверяет соответствие требованию ТЗ §3.
    """
    from research.code_factory import build_code_from_config
    from research.config import BCH_DERIVED_64_32_CONFIG

    from time import perf_counter

    code = build_code_from_config(
        BCH_DERIVED_64_32_CONFIG
    )
    start = perf_counter()

    compact = build_compact_syndrome_table(
        parity_check_matrix=code.parity_check_matrix,
        max_error_weight=4,
    )
    elapsed = perf_counter() - start

    # Требование ТЗ §3 для BCH-derived [64,32], t=4
    assert compact.pattern_count == 679121
    assert compact.entry_count == 679121
    assert compact.collision_count == 0

    # Sanity check: не должно быть медленных
    assert elapsed < 30.0
