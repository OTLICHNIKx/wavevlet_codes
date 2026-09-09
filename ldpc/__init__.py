"""Семейство LDPC-кодов проекта.

LDPC рассматривается как обычный линейный блочный код: пакет
предоставляет только матрицы G/H и стандартное линейное кодирование.
Специальный LDPC-декодер не реализуется — декодирование выполняется
существующими syndrome / Chase / MLD декодерами через общий pipeline.
"""

from .code import LDPCCode
from .construction import (
    combination_index,
    column_masks,
    exact_minimum_distance_by_enumeration,
    generator_from_parity_check,
    matrix_from_hex_rows,
    matrix_to_hex_rows,
    minimum_distance_certificate,
    parity_check_from_generator,
    syndromes_for_combinations,
    trim_matrix_to_width,
    validate_ldpc_matrices,
    weight_profile,
)
from .presets import LDPC_16_8, LDPC_32_16, LDPC_64_32

__all__ = [
    "LDPCCode",
    "LDPC_16_8",
    "LDPC_32_16",
    "LDPC_64_32",
    "matrix_to_hex_rows",
    "matrix_from_hex_rows",
    "trim_matrix_to_width",
    "parity_check_from_generator",
    "generator_from_parity_check",
    "validate_ldpc_matrices",
    "weight_profile",
    "exact_minimum_distance_by_enumeration",
    "column_masks",
    "combination_index",
    "syndromes_for_combinations",
    "minimum_distance_certificate",
]