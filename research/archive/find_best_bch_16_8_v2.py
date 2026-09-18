from __future__ import annotations

from itertools import combinations, permutations
from dataclasses import dataclass

import numpy as np

from bch.derived import (
    build_systematic_generator_matrix,
    shorten_systematic_generator_matrix,
    puncture_systematic_generator_matrix_at,
    build_systematic_parity_check_matrix,
)
from bch.code import BCHCode
from research.distance_analysis import (
    analyze_small_code,
)


@dataclass(frozen=True)
class Candidate16_8:
    shortening_coordinates: tuple[int, ...]
    puncture_coordinates: tuple[int, ...]
    d_min: int
    minimum_weight_count: int
    weight_enumerator: tuple[int, ...]


def find_best_bch_derived_16_8_v2() -> Candidate16_8:
    """
    Ищет лучший BCH-derived [16,8] код.

    Перебираем:
      - shortening: выбор 13 информационных бит из 21 → C(21,13) = 20349 вариантов
        (ограничим несколькими разумными подмножествами)
      - puncture: C(18,2) = 153

    Для ускорения ограничим shortening несколькими стратегиями.
    """
    parent = BCHCode.primitive(m=5, designed_distance=5, first_root=1)
    systematic = build_systematic_generator_matrix(parent.generator_matrix)
    G = systematic.generator_matrix  # [21, 31] систематический вид
    k_parent, n_parent = G.shape

    print(f"Родительский BCH: [{n_parent}, {k_parent}, d>=5]")

    # Стратегии shortening: выбрать k_short из k_parent информационных бит.
    # В систематической форме информационные биты — первые k_parent.
    # После shortening остаются k_new = k_parent - s = 21 - 13 = 8.
    # Всего C(21,13) = 20349 — слишком много. Ограничим:
    #   1. первые 13 (стандартное)
    #   2. последние 13
    #   3. равномерно распределённые
    #   4. случайная выборка (если RNG будет)
    k_target = 8
    s = k_parent - k_target  # 13

    shortening_strategies = [
        ("first", tuple(range(s))),
        ("last", tuple(range(k_parent - s, k_parent))),
        ("evenly", tuple(np.linspace(0, k_parent-1, s, dtype=int))),
        ("middle", tuple(range((k_parent-s)//2, (k_parent-s)//2 + s))),
    ]

    best: Candidate16_8 | None = None

    for strat_name, short_coords in shortening_strategies:
        print(f"Shortening strategy: {strat_name}")

        # Для произвольных координат shortening нужно перестроить код.
        # Временно используем стандартный shortening с последующей перестановкой.
        shortened = shorten_systematic_generator_matrix(
            generator_matrix=G,
            shortening_count=s,
        )

        # Если координаты не первые, применим перестановку столбцов.
        if short_coords != tuple(range(s)):
            # Определяем, какие остались
            remaining_info = [
                c for c in range(k_parent) if c not in short_coords
            ]
            remaining_parity = list(range(k_parent, n_parent))

            # Новый порядок: сначала оставшиеся информационные, потом parity
            new_order = remaining_info + remaining_parity
            shortened = G[:, new_order].copy()

        # Теперь shortened = [8, 18].
        assert shortened.shape == (8, 18)

        for p1, p2 in combinations(range(8, 18), 2):
            # Выказываем только проверочные биты (после первых 8).
            try:
                punctured = puncture_systematic_generator_matrix_at(
                    generator_matrix=shortened,
                    puncture_coordinates=(p1, p2),
                )
                h = build_systematic_parity_check_matrix(punctured)
                analysis = analyze_small_code(punctured, h)

                cand = Candidate16_8(
                    shortening_coordinates=short_coords,
                    puncture_coordinates=(p1, p2),
                    d_min=analysis.d_min,
                    minimum_weight_count=analysis.minimum_weight_count,
                    weight_enumerator=analysis.weight_enumerator,
                )

                if best is None or (
                    cand.d_min > best.d_min
                ) or (
                    cand.d_min == best.d_min
                    and cand.minimum_weight_count < best.minimum_weight_count
                ):
                    best = cand

            except Exception as e:
                continue

    return best


def main() -> None:
    print("Расширенный поиск BCH-derived [16,8]...")
    best = find_best_bch_derived_16_8_v2()

    print()
    print("Лучший кандидат:")
    print(f"  shortening = {best.shortening_coordinates}")
    print(f"  puncture = {best.puncture_coordinates}")
    print(f"  d_min = {best.d_min}")
    print(f"  A_dmin = {best.minimum_weight_count}")

    if best.d_min >= 5:
        print("OK: найден код с d_min >= 5")
    else:
        print("Не удалось достичь d_min >= 5 с BCH(31,21,5)")
        print("Возможные альтернативы: extended BCH, BCH(31,16,7) с другими параметрами")


if __name__ == "__main__":
    main()
