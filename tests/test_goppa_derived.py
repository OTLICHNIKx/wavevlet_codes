import numpy as np
import pytest

from bch.matrices import gf2_matrix_rank
from goppa.presets import (
    GOPPA_16_8_CODE,
    GOPPA_32_16_CODE,
    GOPPA_64_32_CODE,
)
from research.distance_analysis import analyze_small_code


DERIVED_CODES = (
    (GOPPA_16_8_CODE, 16, 8, 8),
    (GOPPA_32_16_CODE, 32, 16, 17),
    (GOPPA_64_32_CODE, 64, 32, 40),
)


@pytest.mark.parametrize("code,n,k,parent_k", DERIVED_CODES)
def test_derived_code_has_target_dimension(code, n, k, parent_k) -> None:
    assert (code.n, code.k) == (n, k)
    assert code.parent_code.k == parent_k
    assert gf2_matrix_rank(code.generator_matrix) == k
    assert gf2_matrix_rank(code.parity_check_matrix) == n - k
    assert np.all((code.generator_matrix @ code.parity_check_matrix.T) % 2 == 0)


@pytest.mark.parametrize("code", [GOPPA_16_8_CODE, GOPPA_32_16_CODE])
def test_small_derived_code_exact_distance_matches_bound(code) -> None:
    analysis = analyze_small_code(code.generator_matrix, code.parity_check_matrix)

    # Гарантированная граница конструкции (2*deg+1) обязана выполняться;
    # phase-2 derived subcode (message-functional kernel) может её строго
    # превышать (для 32_16: d_min=8 > bound=7).
    assert analysis.d_min >= code.distance_lower_bound
