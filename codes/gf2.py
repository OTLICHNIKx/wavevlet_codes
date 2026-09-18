"""Единая реализация линейной алгебры над GF(2).

До этого те же алгоритмы дублировались в bch/matrices.py,
reed_solomon/construction.py, ldpc/construction.py и
decode/syndrome_decoding/gf2.py. Все они теперь делегируют сюда.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


def to_binary_matrix(
    values: object,
    name: str = "matrix",
) -> np.ndarray:
    """
    Преобразует вход в бинарную матрицу numpy.

    Значения по модулю 2 не нормируются: вход должен уже
    содержать только 0 и 1.
    """
    matrix = np.asarray(values, dtype=int)

    if matrix.ndim != 2:
        raise ValueError(f"{name} должна быть двумерной матрицей")

    if not np.all((matrix == 0) | (matrix == 1)):
        raise ValueError(f"{name} должна содержать только 0 и 1")

    return matrix.astype(np.uint8)


def to_binary_vector(
    values: Iterable[int],
    name: str = "vector",
) -> np.ndarray:
    """
    Преобразует вход в одномерный бинарный вектор.
    """
    vector = np.asarray(list(values), dtype=int).reshape(-1)

    if not np.all((vector == 0) | (vector == 1)):
        raise ValueError(f"{name} должен содержать только 0 и 1")

    return vector.astype(np.uint8)


def gf2_row_reduce(
    matrix: object,
) -> tuple[np.ndarray, tuple[int, ...]]:
    """
    Приводит бинарную матрицу к приведённому ступенчатому виду (RREF).

    Возвращает:

        reduced_matrix
        pivot_columns
    """
    reduced = to_binary_matrix(matrix, name="matrix").copy()

    row_count, column_count = reduced.shape

    pivot_columns: list[int] = []
    pivot_row = 0

    for column in range(column_count):
        if pivot_row >= row_count:
            break

        candidates = np.flatnonzero(reduced[pivot_row:, column])

        if candidates.size == 0:
            continue

        selected_row = pivot_row + int(candidates[0])

        if selected_row != pivot_row:
            reduced[[pivot_row, selected_row]] = reduced[
                [selected_row, pivot_row]
            ]

        for row in range(row_count):
            if row == pivot_row:
                continue

            if reduced[row, column] == 1:
                reduced[row] ^= reduced[pivot_row]

        pivot_columns.append(column)
        pivot_row += 1

    return reduced, tuple(pivot_columns)


def gf2_matrix_rank(matrix: object) -> int:
    """Ранг бинарной матрицы над GF(2)."""
    _, pivot_columns = gf2_row_reduce(matrix)
    return len(pivot_columns)


def gf2_nullspace_basis(matrix: object) -> np.ndarray:
    """
    Базис ядра матрицы над GF(2): строки x такие, что A @ x.T = 0.
    """
    reduced, pivot_columns = gf2_row_reduce(matrix)

    columns_count = reduced.shape[1]
    pivot_set = set(pivot_columns)
    free_columns = [
        column
        for column in range(columns_count)
        if column not in pivot_set
    ]

    if not free_columns:
        return np.zeros((0, columns_count), dtype=np.uint8)

    basis = np.zeros((len(free_columns), columns_count), dtype=np.uint8)

    for basis_row, free_column in enumerate(free_columns):
        basis[basis_row, free_column] = 1
        for row, pivot_column in enumerate(pivot_columns):
            basis[basis_row, pivot_column] = reduced[row, free_column]

    return basis


def gf2_solve(matrix: object, vector: Iterable[int]) -> np.ndarray:
    """
    Решает систему matrix @ x = vector над GF(2).

    Если решений нет, выбрасывает ValueError.
    Если решений несколько, возвращает одно из них.
    """
    a = to_binary_matrix(matrix, name="matrix")
    b = to_binary_vector(vector, name="vector")

    if a.shape[0] != b.shape[0]:
        raise ValueError(
            "Количество строк матрицы должно совпадать "
            "с длиной правой части"
        )

    rows_count, variables_count = a.shape
    augmented = np.column_stack([a, b]).astype(np.uint8)

    reduced, pivot_columns = gf2_row_reduce(augmented)

    for row in range(rows_count):
        left_part_is_zero = np.all(reduced[row, :variables_count] == 0)
        right_part_is_one = reduced[row, variables_count] == 1

        if left_part_is_zero and right_part_is_one:
            raise ValueError("Система над GF(2) не имеет решений")

    solution = np.zeros(variables_count, dtype=np.uint8)

    for row, pivot_column in enumerate(pivot_columns):
        solution[pivot_column] = reduced[row, variables_count]

    return solution
