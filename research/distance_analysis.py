from __future__ import annotations

import sys
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np

from bch.matrices import to_binary_matrix, gf2_matrix_rank


@dataclass(frozen=True)
class SmallCodeAnalysis:
    """
    Результат полного анализа малого линейного кода
    полным перебором всех 2^k двоичных сообщений.

    Заполняется для k <= 16 (максимум 65536 кодовых слов).
    """

    # Параметры кода.
    n: int
    k: int

    generator_matrix: np.ndarray
    parity_check_matrix: np.ndarray

    # Точное минимальное расстояние.
    d_min: int

    # Полный спектр весов: A[w] = сколько кодовых слов имеет вес w.
    weight_enumerator: tuple[int, ...]

    # Число кодовых слов минимального веса (A_dmin).
    minimum_weight_count: int

    # Пример кодового слова минимального веса.
    example_min_weight_codeword: np.ndarray

    # Пример информационного сообщения, которое кодируется
    # в codeword минимального веса.
    example_min_weight_message: np.ndarray

    def __post_init__(self) -> None:
        # Проверяем согласованность n, k с реальными матрицами.
        gen = to_binary_matrix(
            self.generator_matrix, name="generator_matrix"
        )
        h = to_binary_matrix(
            self.parity_check_matrix, name="parity_check_matrix"
        )

        if gen.shape != (self.k, self.n):
            raise ValueError(
                "generator_matrix должен иметь форму "
                f"{(self.k, self.n)}, получено {gen.shape}"
            )
        if h.shape != (self.n - self.k, self.n):
            raise ValueError(
                "parity_check_matrix должен иметь форму "
                f"{(self.n - self.k, self.n)}, получено {h.shape}"
            )

        # Проверяем rank и ортогональность.
        if gf2_matrix_rank(gen) != self.k:
            raise ValueError(
                f"rank(G) = {gf2_matrix_rank(gen)}, ожидалось k = {self.k}"
            )
        if gf2_matrix_rank(h) != self.n - self.k:
            raise ValueError(
                f"rank(H) = {gf2_matrix_rank(h)}, ожидалось n - k = {self.n - self.k}"
            )
        product = (gen.astype(np.int64) @ h.astype(np.int64).T) % 2
        if not np.all(product == 0):
            raise ValueError("Матрицы G и H не ортогональны: G @ H.T != 0")

        if len(self.weight_enumerator) != self.n + 1:
            raise ValueError(
                "weight_enumerator должен иметь длину n + 1"
            )


def _all_message_bits(k: int) -> Iterable[np.ndarray]:
    """
    Генерирует все 2^k возможных информационных сообщений
    в виде двоичных векторов размера k.
    """
    if k <= 0:
        return
    # Итерация по всем битовым маскам.
    for mask in range(1 << k):
        # little-endian: mask[0] = бит 0 = левый бит сообщения.
        yield np.array(
            [(mask >> i) & 1 for i in range(k)],
            dtype=np.uint8,
        )


def analyze_small_code(
    generator_matrix: np.ndarray,
    parity_check_matrix: np.ndarray,
) -> SmallCodeAnalysis:
    """
    Выполняет полный перебор всех 2^k сообщений,
    вычисляет вес каждого кодового слова и возвращает
    точное d_min и полный weight enumerator.

    Ограничение: k <= 16 (2^16 = 65536 кодовых слов).
    """
    gen = to_binary_matrix(
        generator_matrix, name="generator_matrix"
    )
    h = to_binary_matrix(
        parity_check_matrix, name="parity_check_matrix"
    )

    k, n = gen.shape
    if k != gen.shape[0] or n != h.shape[1]:
        raise ValueError("Матрицы G и H имеют несовместимые размеры")

    if k > 16:
        raise ValueError(
            " analyze_small_code поддерживает только k <= 16"
        )

    if gf2_matrix_rank(gen) != k:
        raise ValueError(
            "generator_matrix должна иметь полный строковый ранг"
        )
    if gf2_matrix_rank(h) != n - k:
        raise ValueError(
            "parity_check_matrix должна иметь полный строковый ранг "
            f"n - k = {n - k}"
        )
    product = (gen.astype(np.int64) @ h.astype(np.int64).T) % 2
    if not np.all(product == 0):
        raise ValueError("G @ H.T != 0: матрицы не ортогональны")

    weight_enumerator = [0] * (n + 1)
    d_min: int | None = None
    minimum_weight_count = 0
    example_min_weight_codeword: np.ndarray | None = None
    example_min_weight_message: np.ndarray | None = None

    for message in _all_message_bits(k):
        codeword = (message @ gen) % 2
        weight = int(np.sum(codeword))
        weight_enumerator[weight] += 1

        # Нулевое слово не учитываем при определении d_min.
        if weight == 0:
            continue

        # Ищем лучшее кодовое слово (минимальный вес, затем
        # меньшее число таких слов — здесь достаточно одного примера).
        if d_min is None or weight < d_min:
            d_min = weight
            minimum_weight_count = 1
            example_min_weight_codeword = codeword.copy()
            example_min_weight_message = message.copy()
        elif weight == d_min:
            minimum_weight_count += 1

    # Защита от потенциальной ошибки.
    if d_min is None:
        # Может произойти только для тривиального кода с k=0.
        raise RuntimeError(
            "Не найдено ни одного ненулевого кодового слова"
        )

    return SmallCodeAnalysis(
        n=n,
        k=k,
        generator_matrix=gen,
        parity_check_matrix=h,
        d_min=d_min,
        weight_enumerator=tuple(weight_enumerator),
        minimum_weight_count=minimum_weight_count,
        example_min_weight_codeword=example_min_weight_codeword,
        example_min_weight_message=example_min_weight_message,
    )


def format_small_code_analysis(analysis: SmallCodeAnalysis) -> str:
    """
    Возвращает краткую человекочитаемую сводку по анализу.
    """
    lines: list[str] = []
    lines.append(
        f"Код: [{analysis.n}, {analysis.k}]  "
        f"rate = {analysis.k / analysis.n:.6f}"
    )
    lines.append(f"d_min = {analysis.d_min}")
    lines.append(
        "weight_enumerator: "
        + " ".join(
            f"A[{w}] = {analysis.weight_enumerator[w]}"
            for w in range(analysis.d_min, analysis.n + 1)
            if analysis.weight_enumerator[w] > 0
        )
    )
    lines.append(
        f"minimum_weight_count = {analysis.minimum_weight_count}"
    )
    lines.append(
        "example min-weight message: "
        + "".join(str(int(b)) for b in analysis.example_min_weight_message)
    )
    lines.append(
        "example min-weight codeword: "
        + "".join(str(int(b)) for b in analysis.example_min_weight_codeword)
    )
    return "\n".join(lines)


__all__ = [
    "SmallCodeAnalysis",
    "analyze_small_code",
    "format_small_code_analysis",
]
