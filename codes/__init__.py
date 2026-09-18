"""Общие утилиты кодов, не зависящие от конкретного семейства."""

from .gf2 import (
    gf2_matrix_rank,
    gf2_nullspace_basis,
    gf2_row_reduce,
    gf2_solve,
    to_binary_matrix,
    to_binary_vector,
)

__all__ = [
    "gf2_matrix_rank",
    "gf2_nullspace_basis",
    "gf2_row_reduce",
    "gf2_solve",
    "to_binary_matrix",
    "to_binary_vector",
]
