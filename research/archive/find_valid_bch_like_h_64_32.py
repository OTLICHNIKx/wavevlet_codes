from dataclasses import replace

import numpy as np

from research.config import DEFAULT_RESEARCH_CONFIG
from research.runner import build_code_from_config


TARGET_CODE_NAME = "wavelet_64_32"


def get_64_32_config():
    for code_config in DEFAULT_RESEARCH_CONFIG.codes:
        if code_config.name == TARGET_CODE_NAME:
            return code_config

    raise ValueError(f"Код {TARGET_CODE_NAME} не найден")


def generate_bch_like_h_candidate(
    rng: np.random.Generator,
    length: int = 32,
    target_weight: int = 18,
) -> tuple[int, ...]:
    """
    Генерирует BCH-like кандидат h.

    Это не настоящий BCH-полином, а структурный циклический
    бинарный фильтр с контролируемым весом.
    """
    h = np.zeros(length, dtype=np.uint8)

    # Обязательные позиции, чтобы фильтр не был вырожденным.
    positions = {0, length - 1}

    # Несколько циклических "орбит", похожих на структурный циклический фильтр.
    steps = (3, 5, 7, 11)

    for step in steps:
        start = int(rng.integers(0, step))

        for position in range(start, length, step):
            positions.add(position)

    # Приводим к нужному весу.
    positions = list(positions)

    if len(positions) > target_weight:
        positions = list(
            rng.choice(
                positions,
                size=target_weight,
                replace=False,
            )
        )

    while len(positions) < target_weight:
        candidate = int(rng.integers(0, length))

        if candidate not in positions:
            positions.append(candidate)

    h[positions] = 1

    # Защита: первый коэффициент оставляем единичным.
    h[0] = 1

    return tuple(int(value) for value in h)


def is_valid_h(h: tuple[int, ...]) -> bool:
    """
    Проверяет, можно ли построить корректный код с данным h.
    """
    base_config = get_64_32_config()

    test_config = replace(
        base_config,
        h=h,
        g=None,
    )

    try:
        build_code_from_config(test_config)
    except ValueError:
        return False

    return True


def main() -> None:
    rng = np.random.default_rng(2026)

    print("Поиск валидных BCH-like h для кода (64,32)")
    print("Ищем h длины 32, которые дают обратимое преобразование")
    print()

    found = 0
    max_found = 10
    max_attempts = 10_000

    for attempt in range(1, max_attempts + 1):
        target_weight = int(rng.integers(14, 23))

        h = generate_bch_like_h_candidate(
            rng=rng,
            length=32,
            target_weight=target_weight,
        )

        if not is_valid_h(h):
            continue

        found += 1

        print("=" * 70)
        print(f"КАНДИДАТ #{found}")
        print("attempt =", attempt)
        print("length =", len(h))
        print("weight =", sum(h))
        print("h =")
        print(h)

        if found >= max_found:
            break

    print()
    print("=" * 70)
    print("Поиск завершён.")
    print("Найдено кандидатов:", found)
    print("=" * 70)


if __name__ == "__main__":
    main()