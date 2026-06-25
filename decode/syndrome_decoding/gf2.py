from typing import Iterable

import numpy as np


def to_binary_vector(values: Iterable[int], name: str = "vector") -> np.ndarray:
    """
    Преобразует вход в бинарный вектор над GF(2).
    """
    vector = np.asarray(list(values), dtype=int).reshape(-1)

    if vector.size == 0:
        raise ValueError(f"{name} не должен быть пустым")

    if not np.all((vector == 0) | (vector == 1)):
        raise ValueError(f"{name} должен содержать только 0 и 1")

    return vector.astype(np.uint8)


def to_binary_matrix(values: Iterable[Iterable[int]], name: str = "matrix") -> np.ndarray:
    """
    Преобразует вход в бинарную матрицу над GF(2).
    """
    matrix = np.asarray(values, dtype=int)

    if matrix.ndim != 2:
        raise ValueError(f"{name} должна быть двумерной матрицей")

    if matrix.size == 0:
        raise ValueError(f"{name} не должна быть пустой")

    if not np.all((matrix == 0) | (matrix == 1)):
        raise ValueError(f"{name} должна содержать только 0 и 1")

    return matrix.astype(np.uint8)


def rref_gf2(matrix: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """
    Приводит матрицу к ступенчатому виду над GF(2).

    Возвращает:
        rref_matrix — преобразованная матрица
        pivot_columns — индексы ведущих столбцов
    """
    a = to_binary_matrix(matrix, name="matrix").copy()

    rows_count, columns_count = a.shape
    pivot_columns: list[int] = []
    pivot_row = 0

    for column in range(columns_count):
        pivot = None

        for row in range(pivot_row, rows_count):
            if a[row, column] == 1:
                pivot = row
                break

        if pivot is None:
            continue

        if pivot != pivot_row:
            a[[pivot_row, pivot]] = a[[pivot, pivot_row]]

        for row in range(rows_count):
            if row != pivot_row and a[row, column] == 1:
                a[row] ^= a[pivot_row]

        pivot_columns.append(column)
        pivot_row += 1

        if pivot_row == rows_count:
            break

    return a, pivot_columns


def nullspace_gf2(matrix: np.ndarray) -> np.ndarray:
    """
    Находит базис ядра матрицы над GF(2).

    Для матрицы A возвращает строки x такие, что:
        A @ x.T = 0
    """
    a = to_binary_matrix(matrix, name="matrix")
    rref_matrix, pivot_columns = rref_gf2(a)

    columns_count = a.shape[1]
    free_columns = [
        column
        for column in range(columns_count)
        if column not in pivot_columns
    ]

    basis_vectors = []

    for free_column in free_columns:
        vector = np.zeros(columns_count, dtype=np.uint8)
        vector[free_column] = 1

        for row, pivot_column in enumerate(pivot_columns):
            if rref_matrix[row, free_column] == 1:
                vector[pivot_column] = 1

        basis_vectors.append(vector)

    if not basis_vectors:
        return np.zeros((0, columns_count), dtype=np.uint8)

    return np.asarray(basis_vectors, dtype=np.uint8)


def solve_gf2(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """
    Решает систему:
        matrix @ x = vector

    Все операции выполняются над GF(2).

    Если решений нет, выбрасывает ValueError.
    Если решений несколько, возвращает одно из них.
    """
    a = to_binary_matrix(matrix, name="matrix")
    b = to_binary_vector(vector, name="vector")

    if a.shape[0] != b.shape[0]:
        raise ValueError(
            "Количество строк матрицы должно совпадать с длиной правой части"
        )

    rows_count, variables_count = a.shape
    augmented = np.column_stack([a, b]).astype(np.uint8)

    pivot_columns: list[int] = []
    pivot_row = 0

    for column in range(variables_count):
        pivot = None

        for row in range(pivot_row, rows_count):
            if augmented[row, column] == 1:
                pivot = row
                break

        if pivot is None:
            continue

        if pivot != pivot_row:
            augmented[[pivot_row, pivot]] = augmented[[pivot, pivot_row]]

        for row in range(rows_count):
            if row != pivot_row and augmented[row, column] == 1:
                augmented[row] ^= augmented[pivot_row]

        pivot_columns.append(column)
        pivot_row += 1

        if pivot_row == rows_count:
            break

    for row in range(rows_count):
        left_part_is_zero = np.all(augmented[row, :variables_count] == 0)
        right_part_is_one = augmented[row, variables_count] == 1

        if left_part_is_zero and right_part_is_one:
            raise ValueError("Система над GF(2) не имеет решений")

    solution = np.zeros(variables_count, dtype=np.uint8)

    for row, pivot_column in enumerate(pivot_columns):
        solution[pivot_column] = augmented[row, variables_count]

    return solution