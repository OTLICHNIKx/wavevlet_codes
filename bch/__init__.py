"""
Пакет реализации бинарных BCH-кодов.
"""

from .cyclotomic import (
    build_all_binary_cyclotomic_cosets,
    build_binary_cyclotomic_coset,
    canonicalize_binary_cyclotomic_coset,
    find_binary_cyclotomic_coset,
    validate_binary_cyclotomic_code_length,
)

from .field import (
    DEFAULT_PRIMITIVE_POLYNOMIALS,
    GF2m,
    create_gf2m,
    integer_polynomial_degree,
)

from .generator import (
    BCHGeneratorResult,
    build_bch_generator_polynomial,
    build_minimal_polynomial,
    evaluate_binary_polynomial_in_field,
    evaluate_extension_field_polynomial,
    multiply_extension_field_polynomials,
    trim_extension_field_polynomial,
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
    "build_all_binary_cyclotomic_cosets",
    "build_binary_cyclotomic_coset",
    "canonicalize_binary_cyclotomic_coset",
    "find_binary_cyclotomic_coset",
    "validate_binary_cyclotomic_code_length",
    "BCHGeneratorResult",
    "build_bch_generator_polynomial",
    "build_minimal_polynomial",
    "evaluate_binary_polynomial_in_field",
    "evaluate_extension_field_polynomial",
    "multiply_extension_field_polynomials",
    "trim_extension_field_polynomial",
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