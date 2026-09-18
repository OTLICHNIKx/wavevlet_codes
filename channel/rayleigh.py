import numpy as np

RAYLEIGH_VARIANTS = ("rayleigh", "rayleigh_awgn")


def _unit_power_rayleigh(rng: np.random.Generator, size: tuple[int, ...]) -> np.ndarray:
    """
    Амплитуда релеевского замирания с E[h^2] = 1.

    h = sqrt(X^2 + Y^2), X, Y ~ N(0, 1/sqrt(2)) — классический
    Rayleigh-огибающий коэффициент (мощность в среднем 1, поэтому
    SNR/EbN0-шкала проекта остаётся осмысленной).
    """
    scale = 1.0 / np.sqrt(2.0)
    x = rng.normal(loc=0.0, scale=scale, size=size)
    y = rng.normal(loc=0.0, scale=scale, size=size)
    return np.sqrt(x * x + y * y)


def rayleigh_fading_channel(
    symbols: np.ndarray,
    noise: np.ndarray,
    *,
    blockwise: bool = True,
    seed: int = 0,
) -> np.ndarray:
    """
    Релеевский канал замираний.

    received = h * signal + noise

    blockwise=True  — квазистатический блоковый фейдинг: один h на
                      строку (кодовое слово), вариант "rayleigh";
    blockwise=False — быстрый i.i.d. по символам фейдинг, вариант
                      "rayleigh_awgn".

    noise — заранее подготовленный гауссов шум (base_noise * sigma),
    форма сохраняется; seed обеспечивает воспроизводимость h.
    """
    symbols = np.asarray(symbols, dtype=float)
    noise = np.asarray(noise, dtype=float)
    if symbols.shape != noise.shape:
        raise ValueError("symbols и noise должны иметь одинаковую форму")
    rng = np.random.default_rng(seed)
    if blockwise:
        h = _unit_power_rayleigh(rng, (symbols.shape[0], 1))
    else:
        h = _unit_power_rayleigh(rng, symbols.shape)
    return h * symbols + noise


def rayleigh_channel(symbols, noise, *, seed: int = 0):
    return rayleigh_fading_channel(symbols, noise, blockwise=True, seed=seed)


def rayleigh_awgn_channel(symbols, noise, *, seed: int = 0):
    return rayleigh_fading_channel(symbols, noise, blockwise=False, seed=seed)
