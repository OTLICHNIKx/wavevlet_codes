import itertools
import time

import numpy as np

from research.config import DEFAULT_RESEARCH_CONFIG
from research.runner import build_code_from_config


def codeword_from_positions(
    generator_matrix: np.ndarray,
    positions: tuple[int, ...],
) -> np.ndarray:
    """
    Строит кодовое слово как XOR выбранных строк G.

    Для линейного кода сообщение с единицами в positions
    даёт кодовое слово, равное сумме соответствующих строк G.
    """
    codeword = np.zeros(generator_matrix.shape[1], dtype=np.uint8)

    for position in positions:
        codeword ^= generator_matrix[position]

    return codeword


def deterministic_search(
    generator_matrix: np.ndarray,
    max_message_weight: int,
) -> tuple[int, tuple[int, ...], np.ndarray]:
    """
    Полностью перебирает сообщения веса 1..max_message_weight.
    """
    k, n = generator_matrix.shape

    best_weight = n + 1
    best_positions: tuple[int, ...] = tuple()
    best_codeword = np.zeros(n, dtype=np.uint8)

    for message_weight in range(1, max_message_weight + 1):
        start_time = time.time()
        checked = 0

        for positions in itertools.combinations(range(k), message_weight):
            checked += 1

            codeword = codeword_from_positions(
                generator_matrix=generator_matrix,
                positions=positions,
            )

            codeword_weight = int(np.sum(codeword))

            if 0 < codeword_weight < best_weight:
                best_weight = codeword_weight
                best_positions = positions
                best_codeword = codeword.copy()

                print()
                print("Найдено лучшее кодовое слово:")
                print("  message_weight =", message_weight)
                print("  positions =", best_positions)
                print("  codeword_weight =", best_weight)

        elapsed = time.time() - start_time

        print()
        print(
            f"Завершён перебор сообщений веса {message_weight}: "
            f"checked={checked}, "
            f"best_weight={best_weight}, "
            f"time={elapsed:.2f}s"
        )

    return best_weight, best_positions, best_codeword


def random_fixed_weight_search(
    generator_matrix: np.ndarray,
    message_weights: range,
    samples_per_weight: int,
    seed: int = 2026,
) -> tuple[int, tuple[int, ...], np.ndarray]:
    """
    Случайный поиск, но не по полностью случайным сообщениям,
    а по сообщениям заданного веса.

    Это полезнее, чем обычный random, потому что можно отдельно
    проверить веса 7, 8, 9, ..., 16.
    """
    rng = np.random.default_rng(seed)

    k, n = generator_matrix.shape

    best_weight = n + 1
    best_positions: tuple[int, ...] = tuple()
    best_codeword = np.zeros(n, dtype=np.uint8)

    for message_weight in message_weights:
        start_time = time.time()

        for _ in range(samples_per_weight):
            positions_array = rng.choice(
                k,
                size=message_weight,
                replace=False,
            )

            positions = tuple(sorted(int(value) for value in positions_array))

            codeword = codeword_from_positions(
                generator_matrix=generator_matrix,
                positions=positions,
            )

            codeword_weight = int(np.sum(codeword))

            if 0 < codeword_weight < best_weight:
                best_weight = codeword_weight
                best_positions = positions
                best_codeword = codeword.copy()

                print()
                print("Найдено лучшее кодовое слово случайным поиском:")
                print("  message_weight =", message_weight)
                print("  positions =", best_positions)
                print("  codeword_weight =", best_weight)

        elapsed = time.time() - start_time

        print()
        print(
            f"Завершён random-поиск для веса {message_weight}: "
            f"samples={samples_per_weight}, "
            f"best_weight={best_weight}, "
            f"time={elapsed:.2f}s"
        )

    return best_weight, best_positions, best_codeword


def main() -> None:
    code_config = next(
        item
        for item in DEFAULT_RESEARCH_CONFIG.codes
        if item.name == "wavelet_64_32"
    )

    code = build_code_from_config(code_config)
    generator_matrix = code.generator_matrix.astype(np.uint8)

    print("Проверка минимального расстояния для wavelet_64_32")
    print("n =", code_config.n)
    print("k =", code_config.k)
    print("h =", code_config.h)

    print()
    print("Этап 1: полный перебор сообщений малого веса")
    deterministic_best = deterministic_search(
        generator_matrix=generator_matrix,
        max_message_weight=6,
    )

    print()
    print("Этап 2: случайный поиск по фиксированным весам сообщений")
    random_best = random_fixed_weight_search(
        generator_matrix=generator_matrix,
        message_weights=range(7, 17),
        samples_per_weight=20_000,
        seed=2026,
    )

    candidates = [deterministic_best, random_best]
    best_weight, best_positions, best_codeword = min(
        candidates,
        key=lambda item: item[0],
    )

    print()
    print("=" * 70)
    print("Итоговая найденная верхняя оценка:")
    print("  найденный вес кодового слова =", best_weight)
    print("  значит d_min <=", best_weight)
    print("  позиции единиц в сообщении =", best_positions)
    print("  кодовое слово =", best_codeword.tolist())
    print("=" * 70)


if __name__ == "__main__":
    main()