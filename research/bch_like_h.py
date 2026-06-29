import numpy as np


def generate_bch_like_h_64_32(seed: int = 42, density: float = 0.25) -> tuple[int, ...]:
    """
    BCH-like генерация h для (64,32).

    Идея:
    - циклическая структура
    - несколько базовых "генераторов"
    - контроль плотности
    """

    rng = np.random.default_rng(seed)

    n = 64

    # 1. базовый шаблон (имитация порождающего полинома)
    base = rng.integers(0, 2, size=8)
    base[0] = 1  # чтобы не было нулевого фильтра

    h = np.zeros(n, dtype=int)

    # 2. циклическое разнесение структуры
    step = n // len(base)

    for i, bit in enumerate(base):
        if bit == 1:
            shift = (i * step) % n
            pattern = np.roll(np.eye(1, n, k=shift, dtype=int)[0], 0)
            h ^= pattern

    # 3. добавляем вторую "BCH-структуру" (чтобы усложнить код)
    for i in range(0, n, 7):
        h[i % n] ^= 1

    # 4. контроль плотности
    ones = np.where(h == 1)[0]
    target = int(n * density)

    if len(ones) > target:
        chosen = rng.choice(ones, size=target, replace=False)
        new_h = np.zeros(n, dtype=int)
        new_h[chosen] = 1
        h = new_h

    # 5. защита от вырождения
    if np.sum(h) < 2:
        h[0] = 1
        h[31] = 1

    return tuple(int(x) for x in h)


def print_h():
    h = generate_bch_like_h_64_32(seed=123, density=0.25)
    print("BCH-like h for (64,32):")
    print(h)


if __name__ == "__main__":
    print_h()