import numpy as np
import pytest

from bch import gf2_matrix_rank
from ldpc import (
    LDPC_16_8,
    LDPC_32_16,
    LDPC_64_32,
    LDPCCode,
    matrix_from_hex_rows,
    matrix_to_hex_rows,
    minimum_distance_certificate,
)
from ldpc.presets import LDPC_16_8 as LDPC_16_8_PRESET

ALL_PRESETS = (LDPC_16_8, LDPC_32_16, LDPC_64_32)


def _all_messages(k: int) -> np.ndarray:
    values = np.arange(1 << k, dtype=np.uint64)[:, None]
    shifts = np.arange(k, dtype=np.uint64)[None, :]
    return ((values >> shifts) & 1).astype(np.uint8)


def _exact_min_weight(generator_matrix: np.ndarray) -> int:
    messages = _all_messages(generator_matrix.shape[0])[1:]
    codewords = (messages @ generator_matrix) % 2
    weights = np.sum(codewords, axis=1)
    return int(weights.min())


@pytest.mark.parametrize("code", ALL_PRESETS)
def test_ldpc_preset_matrix_invariants(code: LDPCCode) -> None:
    assert code.G is code.generator_matrix
    assert code.H is code.parity_check_matrix
    assert code.G.shape == (code.k, code.n)
    assert code.H.shape == (code.n - code.k, code.n)
    assert gf2_matrix_rank(code.G) == code.k
    assert gf2_matrix_rank(code.H) == code.n - code.k
    product = (code.G.astype(np.int64) @ code.H.astype(np.int64).T) % 2
    assert np.all(product == 0)


@pytest.mark.parametrize("code", ALL_PRESETS)
def test_ldpc_encoding_returns_n_bits_and_codewords(code: LDPCCode) -> None:
    rng = np.random.default_rng(17)
    for _ in range(25):
        message = rng.integers(0, 2, size=code.k).astype(np.uint8)
        codeword = code.encode(message)
        assert codeword.shape == (code.n,)
        assert set(codeword.tolist()) <= {0, 1}
        assert code.is_codeword(codeword)
        assert np.array_equal(
            codeword,
            (message.astype(np.int64) @ code.G.astype(np.int64) % 2).astype(
                np.uint8
            ),
        )


@pytest.mark.parametrize("code", ALL_PRESETS)
def test_ldpc_rejects_invalid_input_shapes(code: LDPCCode) -> None:
    with pytest.raises(ValueError):
        code.encode(np.zeros(code.k + 1, dtype=np.uint8))
    with pytest.raises(ValueError):
        code.syndrome(np.zeros(code.n + 1, dtype=np.uint8))
    with pytest.raises(ValueError):
        code.encode(np.full(code.k, 2, dtype=np.uint8))


def test_ldpc_presets_are_deterministic_across_reloads() -> None:
    rebuilt = LDPCCode.from_hex_rows(
        parity_check_hex_rows=matrix_to_hex_rows(LDPC_16_8_PRESET.H),
        n=16,
        k=8,
        name="ldpc_16_8",
    )
    assert np.array_equal(rebuilt.H, LDPC_16_8_PRESET.H)
    assert np.array_equal(rebuilt.G, LDPC_16_8_PRESET.G)
    round_trip = matrix_from_hex_rows(matrix_to_hex_rows(LDPC_16_8_PRESET.H))
    assert np.array_equal(round_trip, LDPC_16_8_PRESET.H)


def test_ldpc_16_8_exact_minimum_distance_is_five() -> None:
    assert _exact_min_weight(LDPC_16_8.G) == 5


def test_ldpc_32_16_exact_minimum_distance() -> None:
    assert _exact_min_weight(LDPC_32_16.G) == 8


def test_ldpc_64_32_minimum_distance_certificate_at_least_nine() -> None:
    assert minimum_distance_certificate(LDPC_64_32.H, 4) == 9


@pytest.mark.parametrize("code", ALL_PRESETS)
def test_ldpc_parity_check_matrices_are_sparse(code: LDPCCode) -> None:
    profile = code.parity_check_weight_profile
    assert profile["min_column_weight"] >= 1
    assert profile["max_row_weight"] <= code.n - code.k - 1
    assert profile["density"] <= 0.34
