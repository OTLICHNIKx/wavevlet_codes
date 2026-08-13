from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from bch.matrices import (
    gf2_matrix_rank,
    gf2_row_reduce,
    to_binary_matrix,
)

from .code import GoppaCode


@dataclass
class GoppaDerivedCode:
    """
    Goppa-derived подкод размерности target_k.

    Строится из parent GoppaCode (K_parent > k_target)
    детерминированным способом:
        1. Приводим G_parent к RREF.
        2. Берём первые k_target линейно независимых строк.
        3. Строим H_sub для G_sub.

    Attributes:
        parent_code: родительский GoppaCode
        generator_matrix: G_sub (target_k x n)
        parity_check_matrix: H_sub ((n - target_k) x n)
        target_k: целевая размерность
        derivation_method: способ выбора подкода (например, "rref_first_k")
        name: имя кода
    """

    parent_code: GoppaCode
    generator_matrix: np.ndarray
    parity_check_matrix: np.ndarray
    target_k: int
    derivation_method: str
    name: str = "Goppa-derived code"

    def __post_init__(self) -> None:
        self.generator_matrix = to_binary_matrix(
            self.generator_matrix, name="generator_matrix"
        )
        self.parity_check_matrix = to_binary_matrix(
            self.parity_check_matrix, name="parity_check_matrix"
        )

        k, n = self.generator_matrix.shape

        if k != self.target_k:
            raise ValueError(
                f"G_sub должна иметь {self.target_k} строк, получено {k}"
            )

        if gf2_matrix_rank(self.generator_matrix) != self.target_k:
            raise ValueError("G_sub не имеет полного строкового ранга")

        h_rows, h_cols = self.parity_check_matrix.shape
        if h_cols != n:
            raise ValueError("H_sub и G_sub имеют несовместимые размеры")

        if gf2_matrix_rank(self.parity_check_matrix) != n - self.target_k:
            raise ValueError(
                "H_sub не имеет полного строкового ранга "
                f"n - k = {n - self.target_k}"
            )

        product = (
            self.generator_matrix.astype(np.int64)
            @ self.parity_check_matrix.astype(np.int64).T
        ) % 2
        if not np.all(product == 0):
            raise ValueError("G_sub @ H_sub.T != 0")

    @property
    def n(self) -> int:
        return self.generator_matrix.shape[1]

    @property
    def k(self) -> int:
        return self.target_k

    @property
    def code_rate(self) -> float:
        return self.k / self.n

    @property
    def distance_lower_bound(self) -> int:
        """
        Нижняя граница для подкода: d_min(sub) >= d_min(parent).
        """
        return self.parent_code.distance_lower_bound

    def encode(self, message: Iterable[int]) -> np.ndarray:
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

    def extract_message(self, codeword: Iterable[int]) -> np.ndarray:
        """
        Извлекает сообщение из корректного кодового слова.

        Поскольку G_sub получена из RREF parent G,
        первые k столбцов G_sub образуют единичную матрицу
        (после перестановки координат).
        """
        word = np.asarray(list(codeword), dtype=np.uint8)
        if len(word) != self.n:
            raise ValueError(
                f"Длина кодового слова должна быть n={self.n}, "
                f"получено {len(word)}"
            )
        if not self.is_codeword(word):
            raise ValueError("Слово не является кодовым")

        # Для систематической формы G = [I_k | P]
        # первые k бит кодового слова = сообщение.
        # Но наша G_sub не обязательно систематическая после RREF parent.
        # Поэтому используем solve_gf2 через existing decode machinery.
        from decode.syndrome_decoding import recover_message_from_codeword

        return recover_message_from_codeword(
            corrected_word=word,
            generator_matrix=self.generator_matrix,
        )

    @classmethod
    def from_parent(
        cls,
        parent_code: GoppaCode,
        target_k: int,
        derivation_method: str = "rref_first_k",
        name: str | None = None,
    ) -> "GoppaDerivedCode":
        """
        Строит Goppa-derived подкод из parent code.

        Алгоритм:
            1. Приводим G_parent к RREF.
            2. Берём первые target_k ненулевых строк.
            3. Строим H_sub как nullspace(G_sub).
        """
        if target_k > parent_code.k:
            raise ValueError(
                f"target_k={target_k} не может быть больше "
                f"parent_k={parent_code.k}"
            )

        if target_k <= 0:
            raise ValueError("target_k должно быть положительным")

        # Приводим G_parent к RREF
        G_parent = parent_code.generator_matrix
        G_rref, pivot_cols = gf2_row_reduce(G_parent)

        # Берём первые target_k строк (они линейно независимы)
        # После RREF ненулевые строки идут первыми
        G_sub = G_rref[:target_k, :].copy()

        # Проверяем, что выбранные строки действительно независимы
        if gf2_matrix_rank(G_sub) != target_k:
            raise RuntimeError(
                "Не удалось выбрать target_k независимых строк "
                "из RREF parent generator matrix"
            )

        # Строим H_sub как nullspace(G_sub) над GF(2)
        # G_sub имеет размер (target_k, n)
        # H_sub должна иметь размер (n - target_k, n) и G_sub @ H_sub.T = 0
        n = G_sub.shape[1]

        # Используем gf2_row_reduce для нахождения nullspace
        # Транспонируем G_sub, приводим к RREF, находим свободные переменные
        G_sub_T = G_sub.T  # (n, target_k)
        G_sub_T_rref, pivot_cols_T = gf2_row_reduce(G_sub_T)

        # Свободные столбцы в G_sub_T — это строки H_sub
        # Но нам нужно решение G_sub @ x = 0, то есть nullspace(G_sub)
        # Это эквивалентно nullspace(G_sub) = rowspan(H_sub)

        # Альтернатива: строим H_sub через RREF G_sub
        # G_sub уже в RREF (первые target_k строк G_rref)
        # Свободные переменные — столбцы не в pivot_cols
        free_cols = [c for c in range(n) if c not in pivot_cols[:target_k]]

        # Базис nullspace: для каждой свободной переменной создаём вектор
        H_rows = []
        for free_col in free_cols:
            vector = np.zeros(n, dtype=np.uint8)
            vector[free_col] = 1
            # Подставляем обратно в RREF G_sub
            for i in range(target_k - 1, -1, -1):
                pivot_col = pivot_cols[i]
                if G_sub[i, free_col] == 1:
                    vector[pivot_col] = 1
            H_rows.append(vector)

        H_sub = np.array(H_rows, dtype=np.uint8)

        # Проверяем размеры
        if H_sub.shape[0] != n - target_k:
            raise RuntimeError(
                f"H_sub должна иметь {n - target_k} строк, "
                f"получено {H_sub.shape[0]}"
            )

        if name is None:
            name = (
                f"Goppa-derived({parent_code.n}, {target_k}, "
                f"d>={parent_code.distance_lower_bound})"
            )

        return cls(
            parent_code=parent_code,
            generator_matrix=G_sub,
            parity_check_matrix=H_sub,
            target_k=target_k,
            derivation_method=derivation_method,
            name=name,
        )
