import numpy as np
import pytest

from bch.matrices import gf2_matrix_rank
from goppa.presets import (
    GOPPA_16_8_PARENT,
    GOPPA_32_16_PARENT,
    GOPPA_64_32_PARENT,
)


PARENT_CODES = (
    GOPPA_16_8_PARENT,
    GOPPA_32_16_PARENT,
    GOPPA_64_32_PARENT,
)


@pytest.mark.parametrize("code", PARENT_CODES)
def test_parent_goppa_matrix_invariants(code) -> None:
    assert gf2_matrix_rank(code.generator_matrix) == code.k
    assert gf2_matrix_rank(code.parity_check_matrix) == code.n - code.k
    assert np.all((code.generator_matrix @ code.parity_check_matrix.T) % 2 == 0)


@pytest.mark.parametrize("code", PARENT_CODES)
def test_parent_encode_has_zero_syndrome(code) -> None:
    message = np.random.default_rng(code.n).integers(0, 2, size=code.k, dtype=np.uint8)
    codeword = code.encode(message)

    assert codeword.shape == (code.n,)
    assert np.all(code.syndrome(codeword) == 0)
