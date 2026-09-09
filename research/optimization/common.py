"""Общая инфраструктура офлайн-оптимизации параметров кодов.

Модуль изолирован от production/research runtime: он только строит
коды существующими конструкторами семейств, считает точные веса для
k <= 16 и строгие синдромные сертификаты, и сохраняет артефакты в
research_results/code_optimization/.

Ничего из этого не импортируется в research.config / code_factory /
runner.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from bch import gf2_matrix_rank, to_binary_matrix
from ldpc.construction import combination_index, syndromes_for_combinations

OUTPUT_DIR = Path("research_results") / "code_optimization"


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def rref(matrix: np.ndarray) -> np.ndarray:
    """Приведение бинарной матрицы к каноническому ступенчатому виду."""
    m = np.asarray(matrix, dtype=np.uint8).copy()
    rows, cols = m.shape
    pivot_row = 0
    for col in range(cols):
        if pivot_row >= rows:
            break
        candidates = np.flatnonzero(m[pivot_row:, col])
        if candidates.size == 0:
            continue
        selected = pivot_row + int(candidates[0])
        if selected != pivot_row:
            m[[pivot_row, selected]] = m[[selected, pivot_row]]
        for row in range(rows):
            if row != pivot_row and m[row, col] == 1:
                m[row] ^= m[pivot_row]
        pivot_row += 1
    return m[:pivot_row]


def code_fingerprint(generator_matrix: np.ndarray) -> str:
    """
    Канонический отпечаток линейного кода: SHA-256 от RREF(G).

    Перестановки/линейные комбинации строк G отпечаток не меняют.
    """
    canonical = rref(generator_matrix).tobytes()
    return hashlib.sha256(canonical).hexdigest()[:16]


def matrices_valid(
    generator: np.ndarray,
    parity_check: np.ndarray,
    n: int,
    k: int,
) -> bool:
    if generator.shape != (k, n) or parity_check.shape != (n - k, n):
        return False
    if gf2_matrix_rank(generator) != k:
        return False
    if gf2_matrix_rank(parity_check) != n - k:
        return False
    product = (
        generator.astype(np.int64) @ parity_check.astype(np.int64).T
    ) % 2
    return bool(np.all(product == 0))


def exact_weight_enumerator(generator_matrix: np.ndarray) -> dict[str, Any]:
    """
    Точный весовой enumerатор полного перебора 2^k слов (k <= 16).

    Возвращает d_min, полный weight_enumerator, A_dmin и пример
    минимального слова (как в research.distance_analysis, быстрее).
    """
    generator = to_binary_matrix(
        generator_matrix, name="generator_matrix"
    )
    k, n = generator.shape
    if k > 16:
        raise ValueError("Поддержан только k <= 16")
    messages = (
        (np.arange(1 << k, dtype=np.uint64)[:, None]
         >> np.arange(k, dtype=np.uint64)[None, :]) & 1
    ).astype(np.uint8)
    codewords = (messages @ generator) % 2
    weights = np.sum(codewords, axis=1)
    enumerator = [0] * (n + 1)
    for weight in weights.tolist():
        enumerator[weight] += 1
    nonzero = [w for w in range(1, n + 1) if enumerator[w]]
    d_min = min(nonzero)
    example_index = int(np.flatnonzero(weights == d_min)[0])
    return {
        "d_min_exact": int(d_min),
        "weight_enumerator": tuple(enumerator),
        "A_dmin": int(enumerator[d_min]),
        "example_min_weight_message": int(example_index),
        "example_min_weight_codeword": codewords[example_index].tolist(),
    }


class ViolationScorer:
    """
    Число нарушений сертификата d_min >= 2w+1 для матрицы H.

    Нарушение = подмножество столбцов размера <= w с нулевым
    синдромом либо пара различных подмножеств с равными синдромами.
    violations == 0 <=> строгий сертификат d_min >= 2w + 1 выполнен.
    Комбинации предвычислены; оценка кандидата ~ O(C(n,<=w)) XOR+sort.
    """

    def __init__(self, columns: int, w: int) -> None:
        self.sizes = list(range(1, w + 1))
        self.combos: dict[int, np.ndarray] = {}
        offsets: list[int] = []
        position = 0
        for size in self.sizes:
            combo = combination_index(columns, size)
            self.combos[size] = combo
            offsets.append(position)
            position += combo.shape[0]
        self.total = position
        self.offsets = np.array(offsets, dtype=np.intp)

    def _members(self, flat_index: int) -> list[int]:
        size_pos = int(
            np.searchsorted(self.offsets, flat_index, side="right")
        ) - 1
        size = self.sizes[size_pos]
        row = flat_index - int(self.offsets[size_pos])
        return [int(column) for column in self.combos[size][row]]

    def violations(self, parity_check: np.ndarray) -> tuple[int, list[int]]:
        parity_check = np.asarray(parity_check, dtype=np.uint8)
        rows = parity_check.shape[0]
        if rows > 62:
            raise ValueError("Скорер поддержан для H с числом строк <= 62")
        masks = np.zeros(parity_check.shape[1], dtype=np.int64)
        for row in range(rows):
            masks ^= parity_check[row].astype(np.int64) * np.int64(1 << row)
        syndromes = np.empty(self.total, dtype=np.int64)
        for index, size in enumerate(self.sizes):
            combo = self.combos[size]
            start = int(self.offsets[index])
            syndromes[start:start + combo.shape[0]] = (
                syndromes_for_combinations(masks, combo)
            )
        order = np.argsort(syndromes, kind="stable")
        sorted_syndromes = syndromes[order]
        zero_positions = np.flatnonzero(sorted_syndromes == 0)
        duplicate_positions = np.flatnonzero(
            sorted_syndromes[1:] == sorted_syndromes[:-1]
        )
        total = int(zero_positions.size + duplicate_positions.size)
        example: list[int] = []
        if total:
            if zero_positions.size:
                position = int(zero_positions[0])
                example = self._members(int(order[position]))
            else:
                position = int(duplicate_positions[0])
                left = set(self._members(int(order[position])))
                right = set(self._members(int(order[position + 1])))
                example = sorted(left ^ right)
        return total, example


def distance_certificate(parity_check: np.ndarray, w: int) -> int:
    """Строгий сертификат: возвращает 2w+1, если d_min >= 2w+1 доказано."""
    from ldpc import minimum_distance_certificate

    return minimum_distance_certificate(parity_check, w)


def upper_bound_low_weight_search(
    generator_matrix: np.ndarray,
    *,
    exhaustive_message_weight: int = 3,
    random_weights: Iterable[int] = range(4, 17),
    samples_per_weight: int = 20_000,
    seed: int = 2026,
) -> tuple[int, tuple[int, ...]]:
    """
    Верхняя оценка d_min: полный перебор сообщений веса <= t плюс
    случайные сообщения фиксированных весов. Даёт ТОЛЬКО верхнюю
    оценку (найденный вес слова), нижнюю границу не доказывает.
    """
    generator = to_binary_matrix(
        generator_matrix, name="generator_matrix"
    )
    k, n = generator.shape
    best_weight = n + 1
    best_positions: tuple[int, ...] = ()
    for weight in range(1, exhaustive_message_weight + 1):
        for positions in itertools.combinations(range(k), weight):
            codeword = np.zeros(n, dtype=np.uint8)
            for position in positions:
                codeword ^= generator[position]
            codeword_weight = int(np.sum(codeword))
            if 0 < codeword_weight < best_weight:
                best_weight = codeword_weight
                best_positions = positions
    rng = np.random.default_rng(seed)
    for message_weight in random_weights:
        if message_weight <= exhaustive_message_weight or message_weight > k:
            continue
        for _ in range(samples_per_weight):
            positions = tuple(
                sorted(
                    int(value)
                    for value in rng.choice(k, size=message_weight, replace=False)
                )
            )
            codeword = np.zeros(n, dtype=np.uint8)
            for position in positions:
                codeword ^= generator[position]
            codeword_weight = int(np.sum(codeword))
            if 0 < codeword_weight < best_weight:
                best_weight = codeword_weight
                best_positions = positions
    return best_weight, best_positions


def save_json(name: str, payload: Any, directory: Path | None = None) -> Path:
    target = directory if directory is not None else ensure_output_dir()
    target.mkdir(parents=True, exist_ok=True)
    path = target / name
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=list),
        encoding="utf-8",
    )
    return path


def load_json(name: str) -> Any:
    return json.loads((OUTPUT_DIR / name).read_text(encoding="utf-8"))


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)
