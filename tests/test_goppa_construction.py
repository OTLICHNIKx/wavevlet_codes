import pytest

from goppa.construction import evaluate_goppa_polynomial, is_square_free
from goppa.presets import (
    GOPPA_16_8_CONSTRUCTION,
    GOPPA_32_16_CONSTRUCTION,
    GOPPA_64_32_CONSTRUCTION,
)


CONSTRUCTIONS = (
    (GOPPA_16_8_CONSTRUCTION, 4, 2, 16),
    (GOPPA_32_16_CONSTRUCTION, 5, 3, 32),
    (GOPPA_64_32_CONSTRUCTION, 6, 4, 64),
)


@pytest.mark.parametrize("construction,m,degree,n", CONSTRUCTIONS)
def test_goppa_construction_conditions(construction, m, degree, n) -> None:
    assert construction.m == m
    assert construction.degree == degree
    assert construction.n == n
    assert len(construction.support) == n
    assert len(set(construction.support)) == n
    assert is_square_free(construction.field, construction.goppa_polynomial)
    assert all(
        evaluate_goppa_polynomial(
            construction.field,
            construction.goppa_polynomial,
            alpha,
        ) != 0
        for alpha in construction.support
    )


def test_full_support_16_8_uses_gf16_coefficients() -> None:
    construction = GOPPA_16_8_CONSTRUCTION

    assert construction.support == tuple(range(16))
    assert construction.goppa_polynomial == (7, 4, 1)
    assert any(coefficient not in (0, 1) for coefficient in construction.goppa_polynomial)
