import numpy as np
import pytest

from bch import gf2_matrix_rank
from reed_solomon import (
    REED_SOLOMON_16_8_CODE,
    REED_SOLOMON_32_16_CODE,
    REED_SOLOMON_64_32_CODE,
    ReedSolomonBinaryCode,
    ReedSolomonConstruction,
    bits_to_symbols,
    symbols_to_bits,
)


def _all_messages(k: int) -> np.ndarray:
    values = np.arange(1 << k, dtype=np.uint64)[:, None]
    shifts = np.arange(k, dtype=np.uint64)[None, :]
    return ((values >> shifts) & 1).astype(np.uint8)


def _exact_binary_distance(code: ReedSolomonBinaryCode) -> tuple[int, np.ndarray]:
    messages = _all_messages(code.k)[1:]
    codewords = (messages @ code.generator_matrix) % 2
    weights = np.sum(codewords, axis=1)
    return int(weights.min()), weights


def test_grs_16_8_binary_matrix_invariants() -> None:
    code = REED_SOLOMON_16_8_CODE
    assert (code.n, code.k) == (16, 8)
    assert code.evaluation_points == (0, 1, 2, 3)
    assert code.column_multipliers == (1, 3, 1, 3)
    assert code.generator_matrix.shape == (8, 16)
    assert code.parity_check_matrix.shape == (8, 16)
    assert gf2_matrix_rank(code.generator_matrix) == 8
    assert gf2_matrix_rank(code.parity_check_matrix) == 8
    assert np.all((code.generator_matrix.astype(np.int64) @ code.parity_check_matrix.astype(np.int64).T) % 2 == 0)


def test_grs_16_8_encoder_matches_matrix_for_all_256_messages() -> None:
    code = REED_SOLOMON_16_8_CODE
    messages = _all_messages(code.k)
    direct = np.vstack([code.encode(message) for message in messages])
    matrix = (messages @ code.generator_matrix) % 2
    assert np.array_equal(direct, matrix)
    assert np.array_equal(code.encode(np.zeros(code.k, dtype=np.uint8)), np.zeros(code.n, dtype=np.uint8))


def test_grs_16_8_binary_minimum_distance_and_weight_distribution() -> None:
    code = REED_SOLOMON_16_8_CODE
    d_min, nonzero_weights = _exact_binary_distance(code)
    assert d_min == 5
    all_weights = np.concatenate((np.array([0]), nonzero_weights))
    distribution = {weight: int(np.count_nonzero(all_weights == weight)) for weight in range(code.n + 1)}
    assert distribution == {0: 1, 1: 0, 2: 0, 3: 0, 4: 0, 5: 24, 6: 44, 7: 40, 8: 45, 9: 40, 10: 28, 11: 24, 12: 10, 13: 0, 14: 0, 15: 0, 16: 0}


def test_grs_encoding_is_linear_and_deterministic() -> None:
    first = REED_SOLOMON_16_8_CODE
    second = ReedSolomonBinaryCode.from_parameters(
        m=4, symbol_n=4, symbol_k=2, primitive_polynomial=0b10011,
        evaluation_points=(0, 1, 2, 3), column_multipliers=(1, 3, 1, 3),
    )
    left = np.array([1, 0, 1, 0, 0, 1, 1, 0], dtype=np.uint8)
    right = np.array([0, 1, 1, 1, 0, 0, 1, 0], dtype=np.uint8)
    assert np.array_equal(first.encode(left ^ right), first.encode(left) ^ first.encode(right))
    assert np.array_equal(first.generator_matrix, second.generator_matrix)
    assert np.array_equal(first.parity_check_matrix, second.parity_check_matrix)


@pytest.mark.parametrize(
    ("points", "multipliers"),
    [((0, 1, 1, 3), (1, 3, 1, 3)), ((0, 1, 2, 3), (1, 3, 0, 3))],
)
def test_grs_rejects_duplicate_points_and_zero_multipliers(points, multipliers) -> None:
    with pytest.raises(ValueError):
        ReedSolomonConstruction.create(
            m=4, symbol_n=4, symbol_k=2, primitive_polynomial=0b10011,
            evaluation_points=points, column_multipliers=multipliers,
        )


def test_symbol_bit_conversions_round_trip() -> None:
    code = REED_SOLOMON_16_8_CODE
    symbols = np.array([0, 1, 3, 15], dtype=np.int64)
    assert np.array_equal(bits_to_symbols(symbols_to_bits(symbols, code.field), 4), symbols)


def test_grs_32_16_exact_binary_distance() -> None:
    code = REED_SOLOMON_32_16_CODE
    d_min, _ = _exact_binary_distance(code)
    assert d_min == 6


def test_grs_64_32_has_valid_extended_evaluation_and_proven_symbol_lower_bound() -> None:
    code = REED_SOLOMON_64_32_CODE
    assert (code.n, code.k) == (64, 32)
    assert len(set(code.evaluation_points)) == 16
    assert set(code.evaluation_points) == set(range(16))
    assert all(value != 0 for value in code.column_multipliers)
    assert code.construction.symbol_n - code.construction.symbol_k + 1 == 9
