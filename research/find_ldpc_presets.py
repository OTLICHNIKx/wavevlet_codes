"""Детерминированный поиск замороженных LDPC-матриц для пресетов (n,k).

Целевые расстояния: (16,8) d_min=5, (32,16) d_min=8, (64,32) d_min>=9.

Ключевые факты:
  * d_min(C) = минимальный размер линейно зависимого множества столбцов H;
  * все подмножества столбцов размера <= w имеют ненулевые попарно
    различные синдромы  <=>  d_min >= 2w + 1;
  * для k <= 16 d_min считается точно перебором 2^k кодовых слов.

Запуск (одноразовый, результаты замораживаются в ldpc/presets.py):
    python -m research.find_ldpc_presets --size 16_8
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from bch import gf2_matrix_rank
from ldpc import (
    column_masks as _column_masks,
    combination_index as _combination_index,
    matrix_to_hex_rows,
    minimum_distance_certificate,
    parity_check_from_generator,
    syndromes_for_combinations as _syndromes_for_combinations,
    weight_profile,
)


def _subset_syndromes(masks: np.ndarray, size: int) -> np.ndarray:
    return _syndromes_for_combinations(
        masks, _combination_index(len(masks), size)
    )


def certificates_distance_at_least(parity_check: np.ndarray, w: int) -> bool:
    """True <=> d_min(H-кода) >= 2w + 1 (полный сертификат)."""
    return minimum_distance_certificate(parity_check, w) == 2 * w + 1


def exhaustive_min_distance(
    parity_check: np.ndarray, k: int
) -> tuple[int, int, np.ndarray]:
    """
    Точный d_min перебором 2^k сообщений (nullspace-код).

    Возвращает (d_min, word_mask, generator), где word_mask — битовая
    маска кодового слова минимального веса (бит n-1-j соответствует
    столбцу j матрицы H).
    """
    generator = parity_check_from_generator(parity_check)
    if generator.shape[0] != k:
        return -1, 0, generator
    row_masks = [
        sum(int(bit) << (generator.shape[1] - 1 - column)
            for column, bit in enumerate(generator[row]))
        for row in range(k)
    ]
    best_weight = generator.shape[1] + 1
    best_word = 0
    current = 0
    previous_gray = 0
    for counter in range(1, 1 << k):
        gray = counter ^ (counter >> 1)
        changed = previous_gray ^ gray
        bit = changed.bit_length() - 1
        current ^= row_masks[bit]
        weight = current.bit_count()
        if 0 < weight < best_weight:
            best_weight = weight
            best_word = current
        previous_gray = gray
    return best_weight, best_word, generator


def _random_configuration_h(
    rng: np.random.Generator,
    rows: int,
    columns: int,
    column_weights: tuple[int, ...],
    max_row_weight: int,
) -> np.ndarray | None:
    """Случайная H: столбцы веса из column_weights, строки не тяжелее лимита."""
    h = np.zeros((rows, columns), dtype=np.uint8)
    row_weights = np.zeros(rows, dtype=np.int64)
    row_options = [
        np.flatnonzero(row_weights < max_row_weight) for _ in range(columns)
    ]
    for index in range(columns):
        weight = int(rng.choice(column_weights))
        options = np.flatnonzero(row_weights < max_row_weight)
        if options.size < weight:
            return None
        support = rng.choice(options, size=weight, replace=False)
        h[support, index] = 1
        row_weights[support] += 1
    if np.any(row_weights < 3):
        return None
    return h


def search_small(
    n: int,
    k: int,
    target: int,
    seed: int,
    max_row_weight: int,
    column_weights: tuple[int, ...],
    time_limit_sec: float,
) -> dict:
    """
    Поиск H с целевым точным d_min (переборным) для (16,8) и (32,16).

    Стратегия: случайная конфигурация + repair-шаги по мало­весовому
    кодовому слову (перенос единицы в столбце поддержки слова),
    принимаются шаги, не ухудшающие d_min; при улучшении — жадно.
    """
    rng = np.random.default_rng(seed)
    start = time.perf_counter()
    best: dict | None = None
    evaluated = 0
    stall = 0
    h: np.ndarray | None = None
    d = 0

    def evaluate(candidate: np.ndarray) -> int:
        nonlocal evaluated
        evaluated += 1
        if gf2_matrix_rank(candidate) != n - k:
            return -1
        distance, word_mask, _ = exhaustive_min_distance(candidate, k)
        evaluate.last_word_mask = word_mask  # type: ignore[attr-defined]
        return distance

    while time.perf_counter() - start < time_limit_sec:
        if h is None or stall > 3000:
            h = _random_configuration_h(
                rng, n - k, n, column_weights, max_row_weight
            )
            if h is None:
                continue
            d = evaluate(h)
            stall = 0
        if d > 0:
            profile = weight_profile(h)
            if (
                best is None
                or d > best["d_min_exact"]
                or (
                    d == best["d_min_exact"]
                    and profile["density"] < best["profile"]["density"]
                )
            ):
                best = {
                    "n": n,
                    "k": k,
                    "seed": seed,
                    "d_min_exact": int(d),
                    "target": target,
                    "evaluated": evaluated,
                    "profile": profile,
                    "h_hex_rows": list(matrix_to_hex_rows(h)),
                }
        if best is not None and best["d_min_exact"] >= target:
            break
        # repair-шаг: выбрать столбец из поддержки минимального кодового
        # слова и перенести его единицу в другую строку (иногда два
        # столбца); отжиг: допускаем ухудшение с малой вероятностью.
        word_mask = getattr(evaluate, "last_word_mask", 0)
        if d <= 0 or word_mask == 0:
            h = None
            continue
        support_columns = [
            column for column in range(n) if word_mask >> (n - 1 - column) & 1
        ]
        moves = 1 if rng.random() < 0.85 else 2
        candidate = h.copy()
        moved = False
        for _ in range(moves):
            column = support_columns[int(rng.integers(len(support_columns)))]
            set_bits = np.flatnonzero(candidate[:, column])
            unset_options = np.flatnonzero(
                (candidate[:, column] == 0)
                & (candidate.sum(axis=1) < max_row_weight)
            )
            if set_bits.size == 0 or unset_options.size == 0:
                continue
            candidate[int(rng.choice(set_bits)), column] = 0
            candidate[int(rng.choice(unset_options)), column] = 1
            moved = True
        if not moved:
            stall = 10 ** 9
            continue
        candidate_d = evaluate(candidate)
        accept = (
            candidate_d >= d
            or (candidate_d == d - 1 and rng.random() < 0.2)
            or (candidate_d < d - 1 and rng.random() < 0.02)
        )
        if accept:
            h = candidate
            if candidate_d == d:
                stall += 1
            d = candidate_d
        else:
            stall += 1
    if best is None:
        raise RuntimeError(f"поиск не нашёл ни одного кандидата (n={n}, k={k})")
    return best


def _qc_h(
    left_shifts: tuple[int, ...], right_shifts: tuple[int, ...], size: int = 32
) -> np.ndarray:
    h = np.zeros((size, 2 * size), dtype=np.uint8)
    for row in range(size):
        for shift in left_shifts:
            h[row, (row + shift) % size] = 1
        for shift in right_shifts:
            h[row, size + (row + shift) % size] = 1
    return h


class _ViolationScorer:
    """
    Глобальный счётчик нарушений сертификата d_min >= 2w + 1.

    Нарушения: подмножества столбцов размера <= w с нулевым синдромом
    и пары различных подмножеств с совпавшими синдромами (их
    симметрическая разность — зависящее множество веса <= 2w).
    Синдромы всех размеров конкатенируются до сортировки, поэтому
    кросс-размерные коллизии тоже ловятся. Комбинации предвычислены.
    """

    def __init__(self, columns: int, w: int) -> None:
        self.sizes = list(range(1, w + 1))
        self.combos: dict[int, np.ndarray] = {}
        offsets: list[int] = []
        position = 0
        for size in self.sizes:
            combo = _combination_index(columns, size)
            self.combos[size] = combo
            offsets.append(position)
            position += combo.shape[0]
        self.total = position
        self.offsets = np.array(offsets, dtype=np.intp)

    def _all_syndromes(self, masks: np.ndarray) -> np.ndarray:
        syndromes = np.empty(self.total, dtype=np.int64)
        for index, size in enumerate(self.sizes):
            combo = self.combos[size]
            chunk = _syndromes_for_combinations(masks, combo)
            start = int(self.offsets[index])
            syndromes[start:start + combo.shape[0]] = chunk
        return syndromes

    def _members(self, flat_index: int) -> list[int]:
        size_pos = int(
            np.searchsorted(self.offsets, flat_index, side="right")
        ) - 1
        size = self.sizes[size_pos]
        row = flat_index - int(self.offsets[size_pos])
        return [int(column) for column in self.combos[size][row]]

    def violations(self, parity_check: np.ndarray) -> tuple[int, list[int]]:
        """Возвращает (число нарушений, столбцы одного зависящего множества)."""
        masks = _column_masks(parity_check)
        syndromes = self._all_syndromes(masks)
        order = np.argsort(syndromes, kind="stable")
        sorted_syndromes = syndromes[order]
        zeros = np.flatnonzero(sorted_syndromes == 0)
        duplicates = np.flatnonzero(
            sorted_syndromes[1:] == sorted_syndromes[:-1]
        )
        total = int(zeros.size + duplicates.size)
        example: list[int] = []
        if zeros.size:
            example = self._members(int(order[int(zeros[0])]))
        elif duplicates.size:
            position = int(duplicates[0])
            left = self._members(int(order[position]))
            right = self._members(int(order[position + 1]))
            example = sorted(set(left) ^ set(right))
        return total, example


def _row_move(
    h: np.ndarray,
    dependency_columns: list[int],
    rng: np.random.Generator,
    max_row_weight: int,
) -> np.ndarray | None:
    """Переносит единицу случайного столбца зависимости в другую строку."""
    if not dependency_columns:
        return None
    candidate = h.copy()
    column = int(
        dependency_columns[int(rng.integers(len(dependency_columns)))]
    )
    set_bits = np.flatnonzero(candidate[:, column])
    unset_options = np.flatnonzero(
        (candidate[:, column] == 0)
        & (candidate.sum(axis=1) < max_row_weight)
    )
    if set_bits.size == 0 or unset_options.size == 0:
        return None
    candidate[int(rng.choice(set_bits)), column] = 0
    candidate[int(rng.choice(unset_options)), column] = 1
    return candidate


def search_repair_64_32(
    seed: int,
    time_limit_sec: float,
    max_row_weight: int = 8,
    column_weights: tuple[int, ...] = (3, 4),
) -> dict:
    """
    Целевой ремонт нерегулярной разреженной H для (64,32): цель d_min >= 9.

    Две стадии на рестарт: сначала спуск по нарушениям сертификата
    w=3 (зависимости веса <= 6, т.е. d_min >= 7), затем по w=4
    (зависимости веса <= 8, т.е. d_min >= 9). v8 == 0 автоматически
    влечёт v6 == 0 (множество подмножеств <=3 включено в <=4).
    """
    rng = np.random.default_rng(seed)
    n, rows = 64, 32
    scorer6 = _ViolationScorer(n, 3)
    scorer8 = _ViolationScorer(n, 4)
    start = time.perf_counter()
    restarts = 0
    evaluations = 0
    best_v8: int | None = None
    best_h: np.ndarray | None = None

    def descend(
        current: np.ndarray,
        scorer: _ViolationScorer,
        stall_limit: int,
    ) -> tuple[np.ndarray, int]:
        nonlocal evaluations
        violations, columns = scorer.violations(current)
        evaluations += 1
        stall = 0
        while violations > 0 and stall < stall_limit:
            if time.perf_counter() - start > time_limit_sec:
                break
            moved = False
            for _ in range(30):
                if not columns:
                    break
                candidate = _row_move(current, columns, rng, max_row_weight)
                if candidate is None or gf2_matrix_rank(candidate) != rows:
                    continue
                evaluations += 1
                candidate_violations, candidate_columns = scorer.violations(
                    candidate
                )
                if candidate_violations <= violations:
                    if candidate_violations == violations:
                        stall += 1
                    else:
                        stall = 0
                    current = candidate
                    violations, columns = (
                        candidate_violations,
                        candidate_columns,
                    )
                    moved = True
                    break
            if not moved:
                stall += 50
        return current, violations

    while time.perf_counter() - start < time_limit_sec:
        h = _random_configuration_h(
            rng, rows, n, column_weights, max_row_weight
        )
        if h is None or gf2_matrix_rank(h) != rows:
            continue
        restarts += 1
        h, v6 = descend(h, scorer6, stall_limit=5000)
        if v6 > 0:
            print(f"[repair] restart={restarts} stage6 v6={v6} "
                  f"evals={evaluations}", flush=True)
            continue
        h, v8 = descend(h, scorer8, stall_limit=1500)
        if best_v8 is None or v8 < best_v8:
            best_v8, best_h = v8, h.copy()
        if v8 == 0:
            if certificates_distance_at_least(h, 4):
                print(f"[FOUND d>=9 repair] restarts={restarts} "
                      f"evals={evaluations}", flush=True)
                return {
                    "n": n,
                    "k": n - rows,
                    "seed": seed,
                    "restarts": restarts,
                    "evaluations": evaluations,
                    "target_reached": True,
                    "d_min_lower_bound": 9,
                    "profile": weight_profile(h),
                    "h_hex_rows": list(matrix_to_hex_rows(h)),
                }
        print(f"[repair] restart={restarts} v6={v6} v8={v8} "
              f"evals={evaluations}", flush=True)

    if best_h is None:
        raise RuntimeError(
            f"repair-поиск 64_32: ни одного кандидата (seed={seed})"
        )
    bound = 5
    for w in (2, 3, 4):
        if certificates_distance_at_least(best_h, w):
            bound = 2 * w + 1
        else:
            break
    return {
        "n": n,
        "k": n - 32,
        "seed": seed,
        "restarts": restarts,
        "evaluations": evaluations,
        "target_reached": bound >= 9,
        "d_min_lower_bound": bound,
        "profile": weight_profile(best_h),
        "h_hex_rows": list(matrix_to_hex_rows(best_h)),
    }


def search_qc_64_32(
    seed: int,
    time_limit_sec: float,
    left_count: int = 3,
    right_count: int = 3,
) -> dict:
    """QC [C(A)|C(B)] поиск для (64,32): цель d_min >= 9.

    Сертификат w=4 (все подмножества <=4 столбцов с различными
    ненулевыми синдромами) <=> d_min >= 9, поэтому первый прошедший
    кандидат — и есть результат.
    """
    rng = np.random.default_rng(seed)
    start = time.perf_counter()
    evaluated = 0
    gate5 = 0
    fallback: dict | None = None
    while time.perf_counter() - start < time_limit_sec:
        left = tuple(sorted(
            set([0] + [int(rng.integers(1, 32)) for _ in range(left_count - 1)] +
                [int(rng.integers(0, 32))])
        ))
        right = tuple(sorted(
            set([int(rng.integers(0, 32)) for _ in range(right_count)] +
                [int(rng.integers(0, 32))])
        ))
        evaluated += 1
        if len(left) != left_count or len(right) != right_count:
            continue
        h = _qc_h(left, right)
        if gf2_matrix_rank(h) != 32:
            continue
        if not certificates_distance_at_least(h, 2):
            continue
        gate5 += 1
        if fallback is None:
            fallback = {"left": left, "right": right}
        print(
            f"[d>=5 gate] eval={evaluated} gates={gate5} "
            f"{left} {right}",
            flush=True,
        )
        if certificates_distance_at_least(h, 4):
            print(f"[FOUND d>=9] eval={evaluated} {left} {right}", flush=True)
            return {
                "n": 64,
                "k": 32,
                "seed": seed,
                "evaluated": evaluated,
                "gates_passed": gate5,
                "d_min_lower_bound": 9,
                "left_shifts": list(left),
                "right_shifts": list(right),
                "profile": weight_profile(h),
                "h_hex_rows": list(matrix_to_hex_rows(h)),
            }
        if certificates_distance_at_least(h, 3) and fallback is not None:
            if fallback.get("d_bound", 0) < 7:
                fallback = {"left": left, "right": right, "d_bound": 7}
    if fallback is None:
        raise RuntimeError(
            f"QC-поиск 64_32: ни один кандидат не прошёл гейт d>=5 "
            f"(evals={evaluated}, seed={seed})"
        )
    h = _qc_h(fallback["left"], fallback["right"])
    return {
        "n": 64,
        "k": 32,
        "seed": seed,
        "evaluated": evaluated,
        "gates_passed": gate5,
        "d_min_lower_bound": int(fallback.get("d_bound", 5)),
        "left_shifts": list(fallback["left"]),
        "right_shifts": list(fallback["right"]),
        "profile": weight_profile(h),
        "h_hex_rows": list(matrix_to_hex_rows(h)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", choices=["16_8", "32_16", "64_32"], required=True)
    parser.add_argument("--strategy", choices=["qc", "repair"], default="repair")
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--time-limit", type=float, default=900.0)
    parser.add_argument("--max-row-weight", type=int, default=8)
    parser.add_argument("--column-weights", type=str, default="2,3")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.size == "64_32":
        column_weights = tuple(
            int(value) for value in args.column_weights.split(",")
        )
        if args.strategy == "qc":
            result = search_qc_64_32(
                seed=args.seed, time_limit_sec=args.time_limit
            )
        else:
            result = search_repair_64_32(
                seed=args.seed,
                time_limit_sec=args.time_limit,
                max_row_weight=args.max_row_weight,
                column_weights=column_weights,
            )
    else:
        column_weights = tuple(
            int(value) for value in args.column_weights.split(",")
        )
        target = 5 if args.size == "16_8" else 8
        result = search_small(
            int(args.size.split("_")[0]),
            int(args.size.split("_")[1]),
            target=target,
            seed=args.seed,
            max_row_weight=args.max_row_weight,
            column_weights=column_weights,
            time_limit_sec=args.time_limit,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    output = args.output or Path("research_results") / "ldpc_search" / (
        f"ldpc_{args.size}_{args.seed}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("saved:", output)


if __name__ == "__main__":
    main()
