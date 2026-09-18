"""Строгие примитивы поиска кодовых слов малого веса для [64,32].

Математика (для бинарного линейного кода C с проверочной матрицей H):

  * d_min(C) = минимальный размер линейно зависимого множества столбцов H;
  * сертификат: если все подмножества столбцов размера <= w имеют
    ненулевые попарно различные синдромы, то зависимых множеств
    веса <= 2w нет, т.е. d_min >= 2w + 1;
  * MITM: зависимое множество веса a+b (a<=b) существует <=> найдётся
    b-подмножество, синдром которого совпадает с синдромом какого-то
    a-подмножества (при доказанном d_min >= a+b-малое пересечение
    невозможно, но оно проверяется явно).

Все функции детерминированы. Тяжёлые размерности (C(64,5)=7.6M)
перебираются чанками; всё считается точно, без эвристик.
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Iterator

import numpy as np

from bch import gf2_matrix_rank, to_binary_matrix


def column_masks(parity_check: np.ndarray) -> np.ndarray:
    """Столбцы H как int64-маски синдромов."""
    parity_check = to_binary_matrix(parity_check, name="parity_check")
    rows = parity_check.shape[0]
    if rows > 62:
        raise ValueError("rows must be <= 62")
    masks = np.zeros(parity_check.shape[1], dtype=np.int64)
    for row in range(rows):
        masks ^= parity_check[row].astype(np.int64) * np.int64(1 << row)
    return masks


def combination_chunks(
    n: int, size: int, chunk: int = 500_000
) -> Iterator[np.ndarray]:
    """Чанки индексов всех size-подмножеств [0, n)."""
    buffer: list[int] = []
    for comb in itertools.combinations(range(n), size):
        buffer.extend(comb)
        if len(buffer) >= chunk * size:
            yield np.array(buffer, dtype=np.int32).reshape(-1, size)
            buffer = []
    if buffer:
        yield np.array(buffer, dtype=np.int32).reshape(-1, size)


def chunked_subset_syndromes(
    masks: np.ndarray, size: int, chunk: int = 500_000
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """(syndromes int64, combos int16) чанками по всем size-подмножествам."""
    for combo32 in combination_chunks(len(masks), size, chunk):
        syndromes = np.zeros(combo32.shape[0], dtype=np.int64)
        for position in range(size):
            np.bitwise_xor(
                syndromes, masks[combo32[:, position]], out=syndromes
            )
        yield syndromes, combo32.astype(np.int16)


class SubsetSyndromeTable:
    """
    Синдромы всех подмножеств размеров 1..max_size + поиск совпадений.

    Хранит отсортированные синдрomy, для каждого значения — индекс
    ПЕРВОГО подмножества (для извлечения примера) и полную карту
    syndrome -> список индексов (для подсчёта).
    """

    def __init__(self, parity_check: np.ndarray, max_size: int) -> None:
        parity_check = to_binary_matrix(parity_check, name="parity_check")
        masks = column_masks(parity_check)
        self.max_size = max_size
        self._columns = int(parity_check.shape[1])
        sizes = list(range(1, max_size + 1))
        syndromes: list[np.ndarray] = []
        for size in sizes:
            total = math.comb(self._columns, size)
            synd = np.empty(total, dtype=np.int64)
            offset = 0
            for chunk_synd, _combo in chunked_subset_syndromes(masks, size):
                count = chunk_synd.shape[0]
                synd[offset:offset + count] = chunk_synd
                offset += count
            syndromes.append(synd)
        self._size_counts = {
            size: synd.shape[0] for size, synd in zip(sizes, syndromes)
        }
        all_synd = np.concatenate(syndromes)
        order = np.argsort(all_synd, kind="stable")
        self.sorted_syndromes = all_synd[order]
        self.sorted_members = order.astype(np.intp)
        self.total_patterns = int(all_synd.shape[0])
        self.zero_count = int(np.count_nonzero(all_synd == 0))
        unique, counts = np.unique(all_synd, return_counts=True)
        self.collision_pairs = int((counts - 1).sum())
        self.unique_syndromes = int(unique.size)

    # -- свойства сертификата -------------------------------------------
    @property
    def certificate_clean(self) -> bool:
        return self.zero_count == 0 and self.collision_pairs == 0

    # -- MITM против этого таблицы --------------------------------------
    def matching_subsets(
        self,
        parity_check: np.ndarray,
        big_size: int,
        chunk: int = 500_000,
        on_hit=None,
    ) -> int:
        """
        Найти все подмножества размера big_size, синдром которых равен
        синдрому какого-то подмножества из таблицы (размер <= max_size).
        Каждое найденное зависимое множество передаётся в
        on_hit(support_tuple). Возвращает число big-подмножеств,
        для которого Найдено хотя бы одно совпадение (уникальные
        big-подмножества с хитом).
        """
        masks = column_masks(parity_check)
        big_hits = 0
        for syndromes, combos in chunked_subset_syndromes(masks, big_size, chunk):
            positions = np.searchsorted(self.sorted_syndromes, syndromes)
            within = positions < self.sorted_syndromes.shape[0]
            positions_safe = np.where(within, positions, 0)
            matches = within & (
                self.sorted_syndromes[positions_safe] == syndromes
            )
            for hit in np.flatnonzero(matches):
                sorted_position = int(positions[hit])
                small_flat = int(self.sorted_members[sorted_position])
                support = self._decode_union(small_flat, combos[hit])
                big_hits += 1
                if support is not None and on_hit is not None:
                    on_hit(tuple(support))
        return big_hits

    def _decode_union(
        self, small_flat: int, big_row: np.ndarray
    ) -> list[int] | None:
        small = self._member_columns(small_flat)
        union = set(small) | {int(c) for c in big_row}
        if len(union) != len(small) + int(big_row.shape[0]):
            return None  # пересечение: зависимое множество меньшего веса
        return sorted(union)

    def _member_columns(self, flat_index: int) -> list[int]:
        remaining = flat_index
        for size in sorted(self._size_counts):
            count = self._size_counts[size]
            if remaining < count:
                return _unrank_combination(remaining, self._columns, size)
            remaining -= count
        raise IndexError("flat index out of table range")


def _unrank_combination(rank: int, n: int, size: int) -> list[int]:
    """Декомбинация: rank-ое combination (lexicographic) из C(n, size)."""
    result: list[int] = []
    previous = -1
    remaining = size
    for position in range(n):
        if remaining == 0:
            break
        # число комбинаций с этим первым элементом
        count = math.comb(n - position - 1, remaining - 1)
        if rank < count:
            result.append(position)
            remaining -= 1
            rank -= 0
            previous = position
        else:
            rank -= count
    del previous
    return result


# ------------------------------------------------------------------
# Решение c = m·G над GF(2)
# ------------------------------------------------------------------

def solve_message(
    generator_matrix: np.ndarray, codeword: np.ndarray
) -> np.ndarray:
    """
    Вернуть сообщение m (или Raise): m @ G = codeword. G — полный ранг k x n.
    """
    G = to_binary_matrix(generator_matrix, name="generator_matrix")
    k, n = G.shape
    # Gauged matrix [G^T | c]: reduce columns via rows of G.
    work = G.astype(np.int64).copy()
    target = codeword.astype(np.int64) % 2
    coefficients = np.zeros(k, dtype=np.int64)
    # row reduce G keeping pivot mapping
    R = G.copy()
    E = np.eye(k, dtype=np.int64)  # E @ G = R
    pivot_row = 0
    pivot_columns: list[int] = []
    for column in range(n):
        if pivot_row >= k:
            break
        candidates = np.flatnonzero(R[pivot_row:, column])
        if candidates.size == 0:
            continue
        selected = pivot_row + int(candidates[0])
        if selected != pivot_row:
            R[[pivot_row, selected]] = R[[selected, pivot_row]]
            E[[pivot_row, selected]] = E[[selected, pivot_row]]
        for row in range(k):
            if row != pivot_row and R[row, column]:
                R[row] ^= R[pivot_row]
                E[row] ^= E[pivot_row]
        pivot_columns.append(column)
        pivot_row += 1
    if pivot_row != k:
        raise ValueError("generator не полного ранга")
    # represent target in rref basis: reduce against rows of R
    y = target.copy()
    multiplier = np.zeros(k, dtype=np.int64)
    for index, column in enumerate(pivot_columns):
        if y[column]:
            y ^= R[index]
            multiplier[index] ^= 1
    if np.any(y != 0):
        raise ValueError("слово не принадлежит коду")
    m = (multiplier @ E) % 2
    assert np.array_equal((m @ G) % 2, target % 2)
    return m.astype(np.uint8)


def word_from_support(support: tuple[int, ...], n: int) -> np.ndarray:
    word = np.zeros(n, dtype=np.uint8)
    word[list(support)] = 1
    return word


def capture_baseline(code) -> dict[str, Any]:
    """Снимок существующего кода: матрицы, ранги, ортогональность, fp."""
    from research.optimization.common import (
        code_fingerprint,
        matrices_valid,
    )

    generator = to_binary_matrix(code.generator_matrix, name="generator")
    parity_check = to_binary_matrix(code.parity_check_matrix, name="H")
    return {
        "n": int(code.n),
        "k": int(code.k),
        "rate": code.k / code.n,
        "rank_G": int(gf2_matrix_rank(generator)),
        "rank_H": int(gf2_matrix_rank(parity_check)),
        "orthogonality_GHT_zero": bool(np.all(
            (generator.astype(np.int64) @ parity_check.astype(np.int64).T) % 2 == 0
        )),
        "matrices_valid": matrices_valid(generator, parity_check, code.n, code.k),
        "fingerprint_G": code_fingerprint(generator),
        "fingerprint_H": code_fingerprint(parity_check),
    }


def refine_certificate(
    parity_check: np.ndarray, max_size: int
) -> dict[str, Any]:
    """Полный сертификат d >= 2*max_size+1 с метриками."""
    table = SubsetSyndromeTable(parity_check, max_size)
    return {
        "max_error_size": max_size,
        "guaranteed_d_min_lower_bound": (
            2 * max_size + 1 if table.certificate_clean else None
        ),
        "patterns_checked": table.total_patterns,
        "zero_syndrome_count": table.zero_count,
        "collision_count": table.collision_pairs,
        "clean": table.certificate_clean,
    }


def find_weight(
    parity_check: np.ndarray,
    weight: int,
    tables: dict[int, SubsetSyndromeTable],
    split: tuple[int, int] | None = None,
) -> set[tuple[int, ...]]:
    """
    Все зависимые множества столбцов веса exactly `weight`.

    По умолчанию 9=(4+5), 10=(5+5 self), 11=(5+6). Альтернативный
    split (small, big) задаётся явно — для независимого кросс-контроля
    тем же кодом, но с другим разбиением.
    """
    supports: set[tuple[int, ...]] = set()
    if split is None:
        big = (weight + 1) // 2
        small = weight - big
    else:
        small, big = split
    if small != big:
        table = tables.get(small)
        if table is None:
            raise ValueError(f"no table for small size {small}")
        table.matching_subsets(
            parity_check,
            big,
            on_hit=lambda support: supports.add(support)
            if len(support) == weight
            else None,
        )
        return supports
    _self_collision(parity_check, big, supports)
    return supports


def _self_collision(
    parity_check: np.ndarray,
    size: int,
    supports: set[tuple[int, ...]],
    chunk: int = 500_000,
) -> None:
    """Зависимые множества веса 2*size: равные синдромы у двух size-подмножеств."""
    masks = column_masks(parity_check)
    synd_parts: list[np.ndarray] = []
    combo_parts: list[np.ndarray] = []
    for syndromes, combos in chunked_subset_syndromes(masks, size, chunk):
        synd_parts.append(syndromes)
        combo_parts.append(combos)
    all_synd = np.concatenate(synd_parts)
    all_combos = np.concatenate(combo_parts)
    del synd_parts, combo_parts
    order = np.argsort(all_synd, kind="stable")
    sorted_synd = all_synd[order]
    del all_synd
    duplicates = np.flatnonzero(sorted_synd[1:] == sorted_synd[:-1])
    for position in duplicates.tolist():
        left = all_combos[int(order[position])]
        right = all_combos[int(order[position + 1])]
        union = {int(c) for c in left} | {int(c) for c in right}
        if len(union) != 2 * size:
            continue
        supports.add(tuple(sorted(union)))


def refine_distance(
    generator_matrix: np.ndarray,
    parity_check: np.ndarray,
    certificate_size: int = 4,
    candidate_weights: tuple[int, ...] = (9, 10),
    progress=None,
) -> dict[str, Any]:
    """
    Полное уточнение d_min существующего [n,k]-кода (без изменения кода).

    1. Сертификат subsets <= certificate_size (для 4 => d >= 9).
    2. MITM по возрастанию веса: найден зависимое множество веса W —
       d_min = W exact (с примером слова/сообщения и A_W).
    3. Иначе lower = max(проверенных)+1.
    """
    parity_check = to_binary_matrix(parity_check, name="parity_check")
    generator_matrix = to_binary_matrix(
        generator_matrix, name="generator_matrix"
    )
    n = parity_check.shape[1]
    result: dict[str, Any] = {}
    tables: dict[int, SubsetSyndromeTable] = {}
    base_table = SubsetSyndromeTable(parity_check, certificate_size)
    tables[certificate_size] = base_table
    certificate = refine_certificate(parity_check, certificate_size)
    result["certificate"] = certificate
    if not certificate["clean"]:
        result["status"] = "certificate_failed"
        return result
    lower = 2 * certificate_size + 1
    for weight in sorted(candidate_weights):
        if weight <= lower - 1:
            continue
        small = weight - (weight + 1) // 2
        if small not in tables:
            tables[small] = SubsetSyndromeTable(parity_check, small)
        if progress:
            progress(f"MITM weight={weight}")
        supports = find_weight(parity_check, weight, tables)
        if supports:
            support = min(supports)
            word = word_from_support(support, n)
            message = solve_message(generator_matrix, word)
            result.update(
                {
                    "status": "exact",
                    "d_min_exact": int(weight),
                    "A_dmin": len(supports),
                    "min_support": list(support),
                    "min_codeword": [int(v) for v in word],
                    "min_message": [int(v) for v in message],
                    "verified": bool(
                        np.all(
                            (parity_check.astype(np.int64) @ word) % 2 == 0
                        )
                        and int(word.sum()) == weight
                        and np.array_equal(
                            (message @ generator_matrix) % 2, word
                        )
                    ),
                }
            )
            return result
        result.setdefault("cleared_weights", []).append(weight)
        lower = max(lower, weight + 1)
    result["status"] = "lower_bound_only"
    result["d_min_lower_bound"] = int(lower)
    return result
