"""Построение и валидация матриц для Goppa-кодов."""

import numpy as np

from bch.matrices import gf2_matrix_rank, to_binary_matrix


def validate_goppa_matrices(
    generator_matrix: np.ndarray,
    parity_check_matrix: np.ndarray,
) -> None:
    """
    Проверяет, что матрицы G и H для Goppa-кода корректны:
        - G имеет полный строковый ранг k
        - H имеет полный строковый ранг n-k
        - G @ H.T = 0 над GF(2)
    """
    G = to_binary_matrix(generator_matrix, name="generator_matrix")
    H = to_binary_matrix(parity_check_matrix, name="parity_check_matrix")

    k, n = G.shape
    h_rows, h_cols = H.shape

    if h_cols != n:
        raise ValueError("G и H имеют несовместимые размеры")

    if gf2_matrix_rank(G) != k:
        raise ValueError("G не имеет полного строкового ранга k")

    if gf2_matrix_rank(H) != h_rows:
        raise ValueError("H не имеет полного строкового ранга n-k")

    product = (G.astype(np.int64) @ H.astype(np.int64).T) % 2
    if not np.all(product == 0):
        raise ValueError("Матрицы G и H не ортогональны: G @ H.T != 0")


__all__ = [
    "validate_goppa_matrices",
]
