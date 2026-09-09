"""Быстрые инструменты фазы 2.

Ключевая идея: промежуточный код [n0, 16] строится один раз, все 2^16
кодовых слов представляются битовыми матрицами по координатам; затем
d_min ПОСЛЕ выкалывания любого набора P считается как
min(wt(c) - |supp(c) ∩ P|) векторно за миллисекунды. Это позволяет
полные переборы (shortening-множества × puncture-наборы) без
повторных дорогих построений.

Все значения d_min точные (полный перебор 2^16), а не эвристики.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from bch import gf2_matrix_rank, to_binary_matrix

PHASE2_DIR = Path("research_results") / "code_optimization_phase2"


@dataclass
class WordSet:
    """Все слова линейного [n<=64, k<=16] кода в векторном виде."""

    n: int
    k: int
    bits: np.ndarray  # (n, 2^k) uint8 — единицы слова по координатам
    weights: np.ndarray  # (2^k,) int32

    @property
    def nonzero(self) -> np.ndarray:
        return self.weights > 0

    def min_distance(self) -> int:
        nz = self.weights[self.nonzero]
        return int(nz.min()) if nz.size else 0

    def min_distance_punctured(self, coordinates: tuple[int, ...]) -> int:
        """Точный d_min после выкалывания заданных координат."""
        hits = np.zeros(2 ** self.k, dtype=np.int32)
        for coordinate in coordinates:
            hits += self.bits[coordinate].astype(np.int32)
        adjusted = self.weights - hits
        nz = adjusted[adjusted > 0]
        return int(nz.min()) if nz.size else 0

    def punctured_weight_spectrum(self, coordinates: tuple[int, ...]) -> list[int]:
        hits = np.zeros(2 ** self.k, dtype=np.int32)
        for coordinate in coordinates:
            hits += self.bits[coordinate].astype(np.int32)
        adjusted = self.weights - hits
        nonzero = adjusted[adjusted > 0]
        if not nonzero.size:
            return []
        spectrum = [0] * (int(nonzero.max()) + 1)
        for value in nonzero.tolist():
            spectrum[value] += 1
        return spectrum

    def best_puncture(
        self,
        count: int,
        allowed: tuple[int, ...],
        exhaustive_limit: int = 60_000,
        seed: int = 0,
        local_rounds: int = 4000,
    ) -> tuple[int, tuple[int, ...], list[int]]:
        """
        Максимилизировать d_min после выкалывания count координат из allowed.

        Полный перебор при малом C(|allowed|, count), иначе — локальный
        поиск со случайными рестартами. Возвращает
        (d_best, coordinates, weight_spectrum).
        """
        total = _comb(len(allowed), count)
        if total <= exhaustive_limit:
            best_d = -1
            best_set: tuple[int, ...] = ()
            for candidate in itertools.combinations(allowed, count):
                value = self.min_distance_punctured(candidate)
                if value > best_d:
                    best_d = value
                    best_set = candidate
            return best_d, best_set, self.punctured_weight_spectrum(best_set)
        rng = np.random.default_rng(seed)
        best_d = -1
        best_set: tuple[int, ...] = ()
        for restart in range(max(1, local_rounds // 200)):
            current = tuple(
                sorted(
                    int(c)
                    for c in rng.choice(allowed, size=count, replace=False)
                )
            )
            current_d = self.min_distance_punctured(current)
            stall = 0
            while stall < 120:
                index = int(rng.integers(count))
                choice = int(rng.integers(len(allowed)))
                if allowed[choice] in current:
                    stall += 1
                    continue
                candidate = sorted(current)
                candidate[index] = allowed[choice]
                candidate = tuple(candidate)
                value = self.min_distance_punctured(candidate)
                if value > current_d:
                    current, current_d = candidate, value
                    stall = 0
                elif value == current_d:
                    current = candidate
                    stall += 1
                else:
                    stall += 1
            if current_d > best_d:
                best_d, best_set = current_d, current
        return best_d, best_set, self.punctured_weight_spectrum(best_set)


def _comb(a: int, b: int) -> int:
    import math

    return math.comb(a, b)


def wordset_from_generator(generator_matrix: np.ndarray) -> WordSet:
    """
    Строит WordSet полного перебора 2^k сообщений (k <= 16).

    bits[i, m] = i-я координата кодового слова сообщения m — точная
    проверка расстояния по определению (полный перебор).
    """
    generator = to_binary_matrix(generator_matrix, name="generator_matrix")
    k, n = generator.shape
    if k > 16:
        raise ValueError("WordSet поддержан для k <= 16")
    total = 1 << k
    messages = (
        (np.arange(total, dtype=np.uint64)[:, None]
         >> np.arange(k, dtype=np.uint64)[None, :]) & 1
    ).astype(np.uint8)
    codewords = np.zeros((total, n), dtype=np.uint8)
    for bit in range(k):
        selected = messages[:, bit].astype(bool)
        codewords[selected] ^= generator[bit]
    bits = codewords.T.copy()
    weights = codewords.sum(axis=1).astype(np.int32)
    return WordSet(n=n, k=k, bits=bits, weights=weights)


def rank_and_orthogonal_check(
    generator: np.ndarray,
    parity_check: np.ndarray,
    n: int,
    k: int,
) -> dict[str, Any]:
    generator = to_binary_matrix(generator, name="generator")
    parity_check = to_binary_matrix(parity_check, name="parity_check")
    product = (generator.astype(np.int64) @ parity_check.astype(np.int64).T) % 2
    return {
        "gen_shape_ok": generator.shape == (k, n),
        "check_shape_ok": parity_check.shape == (n - k, n),
        "rank_G": int(gf2_matrix_rank(generator)),
        "rank_H": int(gf2_matrix_rank(parity_check)),
        "orthogonality": bool(np.all(product == 0)),
    }
