import csv
import itertools
import os
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from decode.maximum_likelihood_decoding import build_codebook
from research.config import CodeResearchConfig, DEFAULT_RESEARCH_CONFIG
from wavelet import WaveletCode


@dataclass(frozen=True)
class HCandidateScore:
    """
    Оценка одного кандидата h.
    """

    code_name: str
    n: int
    k: int
    h: tuple[int, ...]
    h_length: int
    h_weight: int

    min_distance: int
    min_distance_mode: str

    syndrome_error_weight: int
    syndrome_patterns_count: int
    unique_syndromes_count: int
    syndrome_collisions_count: int

    score: tuple


def build_code_for_h(
    code_config: CodeResearchConfig,
    h: Iterable[int],
) -> WaveletCode:
    """
    Строит вейвлетный код для конкретного h.
    """
    return WaveletCode.from_scaling_coefficients(
        h=tuple(h),
        codeword_length=code_config.n,
        field=2,
        a=code_config.a,
        b=code_config.b,
        shift=code_config.shift,
        name=code_config.name,
    )


def exact_min_distance(generator_matrix: np.ndarray) -> int:
    """
    Точное минимальное расстояние.

    Для линейного кода минимальное расстояние равно
    минимальному ненулевому весу кодового слова.
    """
    _, codewords = build_codebook(generator_matrix)

    weights = np.sum(codewords, axis=1)
    nonzero_weights = weights[weights > 0]

    if len(nonzero_weights) == 0:
        raise ValueError("Нет ненулевых кодовых слов")

    return int(np.min(nonzero_weights))


def heuristic_min_distance(
    generator_matrix: np.ndarray,
    max_message_weight: int = 4,
    random_samples: int = 3000,
    seed: int = 123,
) -> int:
    """
    Приближённая оценка минимального расстояния.

    Используется для k = 32, где полный перебор 2^32 невозможен.
    """
    generator_matrix = np.asarray(generator_matrix, dtype=np.uint8)

    k, n = generator_matrix.shape
    best_weight = n + 1

    # Проверяем все сообщения малого веса.
    for message_weight in range(1, max_message_weight + 1):
        for positions in itertools.combinations(range(k), message_weight):
            codeword = np.zeros(n, dtype=np.uint8)

            for position in positions:
                codeword ^= generator_matrix[position]

            weight = int(np.sum(codeword))

            if 0 < weight < best_weight:
                best_weight = weight

    # Добавляем случайные сообщения.
    rng = np.random.default_rng(seed)

    for _ in range(random_samples):
        message = rng.integers(
            low=0,
            high=2,
            size=k,
            dtype=np.uint8,
        )

        if not np.any(message):
            continue

        codeword = (message @ generator_matrix) % 2
        weight = int(np.sum(codeword))

        if 0 < weight < best_weight:
            best_weight = weight

    if best_weight == n + 1:
        raise ValueError("Не удалось оценить минимальное расстояние")

    return int(best_weight)


def syndrome_collision_stats(
    parity_check_matrix: np.ndarray,
    max_error_weight: int = 2,
) -> tuple[int, int, int]:
    """
    Считает коллизии синдромов для ошибок веса до max_error_weight.

    Возвращает:
        patterns_count
        unique_syndromes_count
        collisions_count
    """
    parity_check_matrix = np.asarray(parity_check_matrix, dtype=np.uint8)

    syndrome_length, codeword_length = parity_check_matrix.shape

    seen_syndromes: set[tuple[int, ...]] = set()
    collisions_count = 0
    patterns_count = 0

    zero_syndrome = tuple(0 for _ in range(syndrome_length))
    seen_syndromes.add(zero_syndrome)
    patterns_count += 1

    for error_weight in range(1, max_error_weight + 1):
        for positions in itertools.combinations(range(codeword_length), error_weight):
            syndrome = np.zeros(syndrome_length, dtype=np.uint8)

            for position in positions:
                syndrome ^= parity_check_matrix[:, position]

            syndrome_key = tuple(int(value) for value in syndrome)
            patterns_count += 1

            if syndrome_key in seen_syndromes:
                collisions_count += 1
            else:
                seen_syndromes.add(syndrome_key)

    return patterns_count, len(seen_syndromes), collisions_count


def generate_h_candidates(
    filter_length: int,
    max_random_candidates: int,
    seed: int,
    exhaustive_threshold_length: int = 14,
) -> list[tuple[int, ...]]:
    """
    Генерирует кандидатов h.

    Для малых длин — полный перебор.
    Для больших длин — случайная генерация.

    Ограничения:
        первый и последний коэффициенты равны 1;
        длина h чётная;
        h не нулевой.
    """
    if filter_length <= 0:
        raise ValueError("filter_length должен быть положительным")

    if filter_length % 2 != 0:
        raise ValueError("filter_length должен быть чётным")

    if filter_length < 2:
        raise ValueError("filter_length должен быть не меньше 2")

    candidates: set[tuple[int, ...]] = set()

    middle_length = filter_length - 2

    if filter_length <= exhaustive_threshold_length:
        for middle_bits in itertools.product([0, 1], repeat=middle_length):
            candidate = (1, *middle_bits, 1)

            if sum(candidate) >= 2:
                candidates.add(candidate)
    else:
        rng = np.random.default_rng(seed)

        while len(candidates) < max_random_candidates:
            middle_bits = rng.integers(
                low=0,
                high=2,
                size=middle_length,
                dtype=np.uint8,
            )

            candidate = (1, *[int(value) for value in middle_bits], 1)

            if sum(candidate) >= 2:
                candidates.add(candidate)

    return sorted(candidates)


def evaluate_h_candidate(
    code_config: CodeResearchConfig,
    h: tuple[int, ...],
    syndrome_error_weight: int,
    exact_min_distance_max_k: int,
    heuristic_random_samples: int,
) -> Optional[HCandidateScore]:
    """
    Проверяет и оценивает один кандидат h.

    Если код не строится, возвращает None.
    """
    try:
        code = build_code_for_h(
            code_config=code_config,
            h=h,
        )
    except Exception:
        return None

    generator_matrix = code.generator_matrix
    parity_check_matrix = code.components["parity_check_matrix"]

    if code_config.k <= exact_min_distance_max_k:
        min_distance = exact_min_distance(generator_matrix)
        min_distance_mode = "exact"
    else:
        min_distance = heuristic_min_distance(
            generator_matrix=generator_matrix,
            max_message_weight=4,
            random_samples=heuristic_random_samples,
            seed=code_config.n + code_config.k + len(h),
        )
        min_distance_mode = "heuristic"

    patterns_count, unique_syndromes_count, collisions_count = syndrome_collision_stats(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=syndrome_error_weight,
    )

    h_weight = int(sum(h))

    # Чем больше score, тем лучше кандидат.
    score = (
        min_distance,
        -collisions_count,
        unique_syndromes_count,
        h_weight,
        -len(h),
    )

    return HCandidateScore(
        code_name=code_config.name,
        n=code_config.n,
        k=code_config.k,
        h=h,
        h_length=len(h),
        h_weight=h_weight,

        min_distance=min_distance,
        min_distance_mode=min_distance_mode,

        syndrome_error_weight=syndrome_error_weight,
        syndrome_patterns_count=patterns_count,
        unique_syndromes_count=unique_syndromes_count,
        syndrome_collisions_count=collisions_count,

        score=score,
    )


def search_h_for_code(
    code_config: CodeResearchConfig,
    filter_lengths: tuple[int, ...],
    max_random_candidates_per_length: int = 300,
    syndrome_error_weight: int = 2,
    exact_min_distance_max_k: int = 16,
    heuristic_random_samples: int = 3000,
    top_n: int = 10,
) -> list[HCandidateScore]:
    """
    Ищет лучшие h для одного кода.
    """
    scores: list[HCandidateScore] = []

    print()
    print(f"Поиск h для {code_config.name}: n={code_config.n}, k={code_config.k}")

    for filter_length in filter_lengths:
        if filter_length > code_config.n:
            continue

        print(f"  filter_length = {filter_length}")

        candidates = generate_h_candidates(
            filter_length=filter_length,
            max_random_candidates=max_random_candidates_per_length,
            seed=code_config.n * 1000 + filter_length,
        )

        valid_count = 0

        for h in candidates:
            score = evaluate_h_candidate(
                code_config=code_config,
                h=h,
                syndrome_error_weight=syndrome_error_weight,
                exact_min_distance_max_k=exact_min_distance_max_k,
                heuristic_random_samples=heuristic_random_samples,
            )

            if score is None:
                continue

            valid_count += 1
            scores.append(score)

        print(f"    candidates = {len(candidates)}, valid = {valid_count}")

    scores.sort(key=lambda item: item.score, reverse=True)

    return scores[:top_n]


def score_to_row(score: HCandidateScore) -> dict:
    """
    Преобразует результат в строку CSV.
    """
    return {
        "code_name": score.code_name,
        "n": score.n,
        "k": score.k,
        "h": " ".join(str(value) for value in score.h),
        "h_length": score.h_length,
        "h_weight": score.h_weight,
        "min_distance": score.min_distance,
        "min_distance_mode": score.min_distance_mode,
        "syndrome_error_weight": score.syndrome_error_weight,
        "syndrome_patterns_count": score.syndrome_patterns_count,
        "unique_syndromes_count": score.unique_syndromes_count,
        "syndrome_collisions_count": score.syndrome_collisions_count,
        "score": str(score.score),
    }


def write_h_search_results(
    scores: list[HCandidateScore],
    output_path: str,
) -> None:
    """
    Сохраняет результаты поиска в CSV.
    """
    if not scores:
        raise ValueError("Нет результатов для сохранения")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows = [score_to_row(score) for score in scores]

    with open(output_path, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_top_scores(scores: list[HCandidateScore]) -> None:
    """
    Печатает лучшие найденные h.
    """
    for index, score in enumerate(scores, start=1):
        print()
        print(f"  #{index}")
        print("  h =", score.h)
        print("  h_length =", score.h_length)
        print("  h_weight =", score.h_weight)
        print("  min_distance =", score.min_distance)
        print("  min_distance_mode =", score.min_distance_mode)
        print("  syndrome_collisions_count =", score.syndrome_collisions_count)
        print("  unique_syndromes_count =", score.unique_syndromes_count)
        print("  score =", score.score)


def main() -> None:
    """
    Запуск поиска сильных h для кодов (16,8), (32,16), (64,32).
    """
    config = DEFAULT_RESEARCH_CONFIG

    filter_lengths_by_code = {
        "wavelet_16_8": (4, 6, 8, 10, 12, 14, 16),
        "wavelet_32_16": (6, 8, 10, 12, 14, 16, 20, 24, 28, 30, 32),
        "wavelet_64_32": (6, 8, 10, 12, 14, 16, 20, 24, 28, 32),
    }

    all_scores: list[HCandidateScore] = []

    for code_config in config.codes:
        scores = search_h_for_code(
            code_config=code_config,
            filter_lengths=filter_lengths_by_code[code_config.name],
            max_random_candidates_per_length=300,
            syndrome_error_weight=2,
            exact_min_distance_max_k=16,
            heuristic_random_samples=3000,
            top_n=10,
        )

        print()
        print("=" * 70)
        print(f"Лучшие h для {code_config.name}")
        print_top_scores(scores)

        all_scores.extend(scores)

    output_path = "research_results/h_search/h_candidates.csv"

    write_h_search_results(
        scores=all_scores,
        output_path=output_path,
    )

    print()
    print("Поиск завершён.")
    print("Файл результатов:", output_path)


if __name__ == "__main__":
    main()