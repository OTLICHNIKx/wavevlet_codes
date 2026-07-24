"""
Пакет реализации бинарных BCH-кодов.
"""

from .field import (
    DEFAULT_PRIMITIVE_POLYNOMIALS,
    GF2m,
    create_gf2m,
    integer_polynomial_degree,
)

from .polynomial import (
    coefficients_to_integer,
    gf2_polynomial_add,
    gf2_polynomial_degree,
    gf2_polynomial_divmod,
    gf2_polynomial_evaluate,
    gf2_polynomial_gcd,
    gf2_polynomial_mod,
    gf2_polynomial_multiply,
    gf2_polynomial_quotient,
    gf2_polynomial_subtract,
    integer_to_coefficients,
    polynomial_to_string,
    validate_binary_polynomial,
)

__all__ = [
    "DEFAULT_PRIMITIVE_POLYNOMIALS",
    "GF2m",
    "create_gf2m",
    "integer_polynomial_degree",
    "coefficients_to_integer",
    "gf2_polynomial_add",
    "gf2_polynomial_degree",
    "gf2_polynomial_divmod",
    "gf2_polynomial_evaluate",
    "gf2_polynomial_gcd",
    "gf2_polynomial_mod",
    "gf2_polynomial_multiply",
    "gf2_polynomial_quotient",
    "gf2_polynomial_subtract",
    "integer_to_coefficients",
    "polynomial_to_string",
    "validate_binary_polynomial",
]