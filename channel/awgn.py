import numpy as np

def awgn_channel(
    symbols: np.ndarray,
    noise_std: float,
    seed: int | None = None,
) -> np.ndarray:
    """
    Канал с аддитивным белым гауссовским шумом.

    received = symbols + noise
    """
    if noise_std < 0:
        raise ValueError("noise_std должен быть неотрицательным")

    symbols = np.asarray(symbols, dtype=float)

    rng = np.random.default_rng(seed)
    noise = rng.normal(loc=0.0, scale=noise_std, size=symbols.shape)

    return symbols + noise