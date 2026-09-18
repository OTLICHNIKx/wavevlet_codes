from __future__ import annotations

from itertools import combinations
from dataclasses import dataclass

import numpy as np

from bch.derived import (
    BCHDerivedCode,
    build_systematic_generator_matrix,
    build_systematic_parity_check_matrix,
    shorten_systematic_generator_matrix,
    puncture_systematic_generator_matrix_at,
)
from bch.code import BCHCode
from research.distance_analysis import (
    SmallCodeAnalysis,
    analyze_small_code,
)


@dataclass(frozen=True)
class PunctureCandidate:
    """Кандидат на оптимальный BCH-derived код."""

    puncture_coordinates: tuple[int, ...]
    d_min: int
    minimum_weight_count: int
    weight_enumerator: tuple[int, ...]
    analysis: SmallCodeAnalysis


def find_best_bch_derived_16_8(
    m: int = 5,
    designed_distance: int = 5,
    shortening_count: int = 13,
) -> PunctureCandidate:
    """
    Ищет лучший BCH-derived [16,8] код через полный перебор
    всех C(18,2) = 153 вариантов выкалывания после укорочения.

    Критерий выбора:
        1. максимальный d_min
        2. при равном d_min — минимальный A_dmin
        3. при равенстве — следующий весовой коэффициент
    """
    # 1. Строим родительский BCH
    parent = BCHCode.primitive(
        m=m,
        designed_distance=designed_distance,
        first_root=1,
    )

    # 2. Приводим к систематическому виду
    systematic = build_systematic_generator_matrix(
        parent.generator_matrix
    )

    # 3. Укорачиваем до [18, 8]
    shortened = shorten_systematic_generator_matrix(
        generator_matrix=systematic.generator_matrix,
        shortening_count=shortening_count,
    )

    assert shortened.shape == (8, 18)

    # 4. Перебираем все пары выкалывания C(18,2)
    best: PunctureCandidate | None = None

    for p1, p2 in combinations(range(18), 2):
        try:
            punctured = puncture_systematic_generator_matrix_at(
                generator_matrix=shortened,
                puncture_coordinates=(p1, p2),
            )

            # Проверка размеров
            assert punctured.shape == (8, 16)

            # Строим H
            h = build_systematic_parity_check_matrix(punctured)

            # Полный анализ
            analysis = analyze_small_code(punctured, h)

            candidate = PunctureCandidate(
                puncture_coordinates=(p1, p2),
                d_min=analysis.d_min,
                minimum_weight_count=analysis.minimum_weight_count,
                weight_enumerator=analysis.weight_enumerator,
                analysis=analysis,
            )

            if best is None:
                best = candidate
                continue

            # Критерий выбора
            if candidate.d_min > best.d_min:
                best = candidate
            elif candidate.d_min == best.d_min:
                if (
                    candidate.minimum_weight_count
                    < best.minimum_weight_count
                ):
                    best = candidate
                elif (
                    candidate.minimum_weight_count
                    == best.minimum_weight_count
                ):
                    # Сравниваем следующие коэффициенты A_{d+1}, A_{d+2}...
                    for w in range(
                        candidate.d_min + 1,
                        min(16 + 1, len(candidate.weight_enumerator)),
                    ):
                        cw = candidate.weight_enumerator[w]
                        bw = best.weight_enumerator[w]
                        if cw < bw:
                            best = candidate
                            break
                        elif cw > bw:
                            break

        except Exception as e:
            # Некоторые комбинации могут приводить к вырожденным матрицам
            print(f"  Пропуск ({p1},{p2}): {e}")
            continue

    if best is None:
        raise RuntimeError("Не найдено ни одного валидного кандидата")

    return best


def main() -> None:
    print("Поиск оптимального BCH-derived [16,8]...")
    print("Родитель: BCH(31, 21, d>=5)")
    print("Shortening: 13 -> [18,8]")
    print("Перебор C(18,2) = 153 варианта puncturing")
    print()

    best = find_best_bch_derived_16_8()

    print("Лучший кандидат:")
    print(f"  puncture_coordinates = {best.puncture_coordinates}")
    print(f"  d_min = {best.d_min}")
    print(f"  A_dmin = {best.minimum_weight_count}")
    print(f"  weight_enumerator: {best.weight_enumerator}")
    print()
    print("Пример min-weight codeword:")
    print(
        "".join(str(int(b)) for b in best.analysis.example_min_weight_codeword)
    )

    if best.d_min < 5:
        print()
        print("ПРЕДУПРЕЖДЕНИЕ: d_min < 5!")
        print("Нужно исследовать альтернативные родительские BCH-коды.")


if __name__ == "__main__":
    main()
