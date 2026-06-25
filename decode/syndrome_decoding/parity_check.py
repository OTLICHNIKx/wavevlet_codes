import numpy as np

from .gf2 import nullspace_gf2, to_binary_matrix


def build_parity_check_matrix_from_generator(generator_matrix: np.ndarray) -> np.ndarray:
    """
    Строит проверочную матрицу H по порождающей матрице G.

    У нас:
        G имеет размер k x n

    Нужно получить H размера (n - k) x n, такую что:
        H @ G.T = 0
    """
    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    parity_check_matrix = nullspace_gf2(generator_matrix)

    if parity_check_matrix.size == 0:
        raise ValueError(
            "Не удалось построить проверочную матрицу: ядро порождающей матрицы пустое"
        )

    product = (parity_check_matrix @ generator_matrix.T) % 2

    if not np.all(product == 0):
        raise ValueError(
            "Проверочная матрица построена некорректно: H @ G.T должно быть равно 0"
        )

    return parity_check_matrix.astype(np.uint8)