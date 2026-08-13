from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from bch.matrices import (
    gf2_matrix_rank,
    to_binary_matrix,
)
from bch.field import GF2m

from .construction import (
    GoppaConstruction,
    evaluate_goppa_polynomial,
)


def build_goppa_parity_check_matrix(
    construction: GoppaConstruction,
) -> np.ndarray:
    """
    Строит бинарную parity-check matrix для parent Goppa code.

    Для binary Goppa code Γ(L, g):
        H[i,j] = coefficient of x^{t-1} in ( (x - α_j) * g'(α_j)^{-1} mod g )

    Альтернативная (упрощённая) форма:
        H[j] = column of g(α_j)^{-1} * [1, α_j, α_j^2, ..., α_j^{t-1}]
        разложенное по бинарному базису.

    Используем вторую форму для простоты и надёжности.
    """
    field = construction.field
    support = construction.support
    g = construction.goppa_polynomial
    t = construction.degree
    n = construction.n
    m = field.m

    # H будет размером (t*m) x n (каждый элемент GF(2^m) -> m бит)
    # Но для Goppa кода rank(H) обычно = n - K, где K >= n - t*m
    # Мы построим расширенную матрицу, затем удалим линейно зависимые строки.

    # Строим H по строкам: для каждого (i, bit_pos) создаём строку длины n
    # где в позиции j стоит бит bit_pos элемента column_elements[i] для α_j.
    rows: list[list[int]] = []

    # Сначала вычисляем все столбцы для всех α_j
    all_columns: list[list[int]] = []

    for j, alpha in enumerate(support):
        g_alpha = evaluate_goppa_polynomial(field, g, alpha)
        if g_alpha == 0:
            raise ValueError(
                f"g(α_{j}) = 0, что запрещено для Goppa-кода"
            )

        g_alpha_inv = field.inverse(g_alpha)

        # Строим столбец: g(α)^{-1} * [1, α, α^2, ..., α^{t-1}]
        column_elements = []
        current_power = 1  # α^0 = 1

        for i in range(t):
            element = field.multiply(g_alpha_inv, current_power)
            column_elements.append(element)
            current_power = field.multiply(current_power, alpha)

        all_columns.append(column_elements)

    # Теперь собираем строки: для каждого (i, bit_pos)
    for i in range(t):
        for bit_position in range(m):
            row = [0] * n
            for j, column_elements in enumerate(all_columns):
                element = column_elements[i]
                bit = (element >> bit_position) & 1
                row[j] = bit
            rows.append(row)

    # Получили (t*m) x n матрицу
    H_expanded = to_binary_matrix(np.array(rows, dtype=np.uint8))

    # Удаляем линейно зависимые строки через RREF
    # Используем gf2_matrix_rank и отбор pivot rows
    rank = gf2_matrix_rank(H_expanded)

    # Приводим к RREF и берём ненулевые строки
    # Для этого используем стандартный алгоритм
    H = H_expanded.copy()
    row_count, col_count = H.shape
    pivot_row = 0
    keep_rows = []

    for col in range(col_count):
        if pivot_row >= row_count:
            break
        candidates = np.flatnonzero(H[pivot_row:, col])
        if candidates.size == 0:
            continue
        selected = pivot_row + int(candidates[0])
        if selected != pivot_row:
            H[[pivot_row, selected]] = H[[selected, pivot_row]]
        for r in range(row_count):
            if r != pivot_row and H[r, col] == 1:
                H[r] ^= H[pivot_row]
        keep_rows.append(pivot_row)
        pivot_row += 1

    H_reduced = H[keep_rows, :]

    return H_reduced


@dataclass
class GoppaCode:
    """
    Parent binary Goppa code Γ(L, g).

    Attributes:
        construction: параметры конструкции
        generator_matrix: G (K x n)
        parity_check_matrix: H ((n-K) x n)
        name: имя кода
    """

    construction: GoppaConstruction
    generator_matrix: np.ndarray
    parity_check_matrix: np.ndarray
    name: str = "Goppa code"

    def __post_init__(self) -> None:
        self.generator_matrix = to_binary_matrix(
            self.generator_matrix, name="generator_matrix"
        )
        self.parity_check_matrix = to_binary_matrix(
            self.parity_check_matrix, name="parity_check_matrix"
        )

        k, n = self.generator_matrix.shape
        h_rows, h_cols = self.parity_check_matrix.shape

        if h_cols != n:
            raise ValueError("H и G имеют несовместимые размеры")

        if gf2_matrix_rank(self.generator_matrix) != k:
            raise ValueError("G не имеет полного строкового ранга")

        if gf2_matrix_rank(self.parity_check_matrix) != h_rows:
            raise ValueError("H не имеет полного строкового ранга")

        product = (
            self.generator_matrix.astype(np.int64)
            @ self.parity_check_matrix.astype(np.int64).T
        ) % 2
        if not np.all(product == 0):
            raise ValueError("G @ H.T != 0")

    @property
    def n(self) -> int:
        return self.generator_matrix.shape[1]

    @property
    def k(self) -> int:
        return self.generator_matrix.shape[0]

    @property
    def code_rate(self) -> float:
        return self.k / self.n

    @property
    def distance_lower_bound(self) -> int:
        return self.construction.distance_lower_bound

    def encode(self, message: Iterable[int]) -> np.ndarray:
        """Кодирует сообщение: c = m @ G mod 2."""
        message_vector = np.asarray(list(message), dtype=np.uint8)
        if len(message_vector) != self.k:
            raise ValueError(
                f"Длина сообщения должна быть k={self.k}, "
                f"получено {len(message_vector)}"
            )
        codeword = (
            message_vector.astype(np.int64)
            @ self.generator_matrix.astype(np.int64)
        ) % 2
        return codeword.astype(np.uint8)

    def syndrome(self, received_word: Iterable[int]) -> np.ndarray:
        """Вычисляет синдром: s = H @ c^T mod 2."""
        word = np.asarray(list(received_word), dtype=np.uint8)
        if len(word) != self.n:
            raise ValueError(
                f"Длина слова должна быть n={self.n}, "
                f"получено {len(word)}"
            )
        syndrome = (
            self.parity_check_matrix.astype(np.int64)
            @ word.astype(np.int64)
        ) % 2
        return syndrome.astype(np.uint8)

    def is_codeword(self, word: Iterable[int]) -> bool:
        return bool(np.all(self.syndrome(word) == 0))

    @classmethod
    def from_construction(
        cls,
        construction: GoppaConstruction,
        name: str | None = None,
    ) -> "GoppaCode":
        """
        Строит parent Goppa code из конструкции.

        1. Строит H (бинарную).
        2. Вычисляет G как базис ядра H (nullspace над GF(2)).
        """
        H = build_goppa_parity_check_matrix(construction)

        # G = nullspace(H) над GF(2)
        # Размерность K = n - rank(H)
        n = construction.n
        rank_H = gf2_matrix_rank(H)
        K = n - rank_H

        # Находим nullspace через приведение к RREF
        # H имеет размер (n-K) x n (после редукции)
        # Нужно найти базис решений H @ x = 0

        # Приводим H к RREF
        H_rref = H.copy()
        row_count, col_count = H_rref.shape
        pivot_cols = []
        pivot_row = 0

        for col in range(col_count):
            if pivot_row >= row_count:
                break
            candidates = np.flatnonzero(H_rref[pivot_row:, col])
            if candidates.size == 0:
                continue
            selected = pivot_row + int(candidates[0])
            if selected != pivot_row:
                H_rref[[pivot_row, selected]] = H_rref[[selected, pivot_row]]
            for r in range(row_count):
                if r != pivot_row and H_rref[r, col] == 1:
                    H_rref[r] ^= H_rref[pivot_row]
            pivot_cols.append(col)
            pivot_row += 1

        # Свободные переменные — это столбцы не в pivot_cols
        free_cols = [c for c in range(col_count) if c not in pivot_cols]

        # Базис nullspace: для каждой свободной переменной создаём вектор
        G_rows = []
        for free_col in free_cols:
            vector = np.zeros(col_count, dtype=np.uint8)
            vector[free_col] = 1
            # Подставляем обратно в RREF
            for i in range(len(pivot_cols) - 1, -1, -1):
                pivot_col = pivot_cols[i]
                if H_rref[i, free_col] == 1:
                    vector[pivot_col] = 1
            G_rows.append(vector)

        G = np.array(G_rows, dtype=np.uint8)

        if name is None:
            name = (
                f"Goppa({n}, {K}, d>={construction.distance_lower_bound})"
            )

        return cls(
            construction=construction,
            generator_matrix=G,
            parity_check_matrix=H,
            name=name,
        )
