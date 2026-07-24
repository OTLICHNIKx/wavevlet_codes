"""
Пакет реализации бинарных BCH-кодов.
"""

from .code import (
    BCHCode,
    to_binary_vector,
)

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

from .matrices import (
    BCHMatrices,
    build_bch_generator_matrix,
    build_bch_matrices,
    build_bch_parity_check_matrix,
    build_shifted_polynomial_matrix,
    gf2_matrix_rank,
    gf2_row_reduce,
    integer_polynomial_to_vector,
    to_binary_matrix,
    validate_bch_matrices,
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
    gf2_polynomial_reciprocal,
    gf2_polynomial_subtract,
    integer_to_coefficients,
    polynomial_to_string,
    validate_binary_polynomial,
)

from .derived import (
    BCHDerivedCode,
    SystematicGeneratorResult,
    build_systematic_generator_matrix,
    build_systematic_parity_check_matrix,
    puncture_systematic_generator_matrix,
    shorten_systematic_generator_matrix,
    validate_systematic_generator_matrix,
)

from .syndrome_analysis import (
    SyndromeCollision,
    SyndromeCollisionAnalysis,
    analyze_syndrome_collisions,
    calculate_error_pattern_syndrome,
    count_error_patterns,
    iter_error_patterns,
    pack_parity_check_columns,
    syndrome_integer_to_bits,
)

__all__ = [
    "BCHCode",
    "to_binary_vector",
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
    "BCHMatrices",
    "build_bch_generator_matrix",
    "build_bch_matrices",
    "build_bch_parity_check_matrix",
    "build_shifted_polynomial_matrix",
    "gf2_matrix_rank",
    "gf2_row_reduce",
    "integer_polynomial_to_vector",
    "to_binary_matrix",
    "validate_bch_matrices",
    "coefficients_to_integer",
    "gf2_polynomial_add",
    "gf2_polynomial_degree",
    "gf2_polynomial_divmod",
    "gf2_polynomial_evaluate",
    "gf2_polynomial_gcd",
    "gf2_polynomial_mod",
    "gf2_polynomial_multiply",
    "gf2_polynomial_quotient",
    "gf2_polynomial_reciprocal",
    "gf2_polynomial_subtract",
    "integer_to_coefficients",
    "polynomial_to_string",
    "validate_binary_polynomial",
    "BCHDerivedCode",
    "SystematicGeneratorResult",
    "build_systematic_generator_matrix",
    "build_systematic_parity_check_matrix",
    "puncture_systematic_generator_matrix",
    "shorten_systematic_generator_matrix",
    "validate_systematic_generator_matrix",
    "SyndromeCollision",
    "SyndromeCollisionAnalysis",
    "analyze_syndrome_collisions",
    "calculate_error_pattern_syndrome",
    "count_error_patterns",
    "iter_error_patterns",
    "pack_parity_check_columns",
    "syndrome_integer_to_bits",
]