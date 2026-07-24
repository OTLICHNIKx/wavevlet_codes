from time import perf_counter
from typing import Protocol

import numpy as np

from bch.derived import BCHDerivedCode

from bch.syndrome_analysis import (
    SyndromeCollisionAnalysis,
    analyze_syndrome_collisions,
    syndrome_integer_to_bits,
)

from research.code_factory import (
    build_code_from_config,
)

from research.config import (
    WAVELET_64_32_CONFIG,
)


class CodeWithParityCheck(Protocol):
    n: int
    k: int
    parity_check_matrix: np.ndarray


def print_analysis(
    code_name: str,
    analysis: SyndromeCollisionAnalysis,
    elapsed_seconds: float,
) -> None:
    print()
    print("-" * 70)

    print(f"Код: {code_name}")
    print(
        "Проверяемый радиус t =",
        analysis.max_error_weight,
    )

    print(
        "Всего шаблонов:",
        analysis.expected_pattern_count,
    )

    print(
        "Проверено шаблонов:",
        analysis.tested_pattern_count,
    )

    print(
        "Уникальных синдромов:",
        analysis.unique_syndrome_count,
    )

    print(
        "Время:",
        f"{elapsed_seconds:.3f} сек.",
    )

    if analysis.collision_free:
        print("Результат: коллизий нет")

        print(
            "Код гарантированно исправляет все ошибки "
            f"веса <= {analysis.max_error_weight}"
        )

        print(
            "Полученная нижняя граница:",
            "d_min >=",
            analysis
            .guaranteed_minimum_distance_lower_bound,
        )

        return

    print("Результат: обнаружена коллизия")

    collision = analysis.first_collision

    if collision is None:
        print(
            "Пример коллизии не был сохранён"
        )
        return

    syndrome_bits = syndrome_integer_to_bits(
        syndrome=collision.syndrome,
        bit_count=analysis.syndrome_bits,
    )

    print(
        "Первая ошибка:",
        collision.first_error_positions,
    )

    print(
        "Вторая ошибка:",
        collision.second_error_positions,
    )

    print(
        "Общий синдром:",
        syndrome_bits.tolist(),
    )

    print(
        "Их сумма образует кодовое слово "
        "на позициях:",
        collision.codeword_positions,
    )

    print(
        "Вес найденного кодового слова:",
        collision.codeword_weight,
    )

    print(
        "Следовательно:",
        f"d_min <= {collision.codeword_weight}",
    )

    print(
        f"Гарантированно исправлять "
        f"{analysis.max_error_weight} ошибки нельзя"
    )


def check_code(
    code_name: str,
    code: CodeWithParityCheck,
) -> None:
    print()
    print("=" * 70)
    print(f"Проверка кода {code_name}")
    print(f"n = {code.n}")
    print(f"k = {code.k}")
    print("=" * 70)

    for max_error_weight in (3, 4):
        start_time = perf_counter()

        analysis = analyze_syndrome_collisions(
            parity_check_matrix=(
                code.parity_check_matrix
            ),
            max_error_weight=max_error_weight,

            # Для t=4 нам достаточно первой коллизии.
            stop_after_first_collision=True,
        )

        elapsed_seconds = (
            perf_counter() - start_time
        )

        print_analysis(
            code_name=code_name,
            analysis=analysis,
            elapsed_seconds=elapsed_seconds,
        )


def main() -> None:
    wavelet_code = build_code_from_config(
        WAVELET_64_32_CONFIG
    )

    bch_derived_code = (
        BCHDerivedCode.from_primitive_parent(
            m=7,
            designed_distance=11,
            shortening_count=60,
            puncture_count=3,
            name="bch_derived_64_32",
        )
    )

    check_code(
        code_name="Wavelet [64,32]",
        code=wavelet_code,
    )

    check_code(
        code_name="BCH-derived [64,32]",
        code=bch_derived_code,
    )


if __name__ == "__main__":
    main()