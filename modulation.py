import numpy as np


def validate_binary_vector(bits: np.ndarray, name: str = "bits") -> np.ndarray:
    """
    Проверяет, что вектор состоит только из 0 и 1.
    """
    vector = np.asarray(bits, dtype=int).reshape(-1)

    if not np.all((vector == 0) | (vector == 1)):
        raise ValueError(f"{name} должен содержать только 0 и 1")

    return vector.astype(np.uint8)


def bpsk_modulate(bits: np.ndarray) -> np.ndarray:
    """
    BPSK-модуляция.

    Используем отображение:
        0 -> +1
        1 -> -1
    """
    bits = validate_binary_vector(bits)

    return 1.0 - 2.0 * bits


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


def bpsk_llr(received_symbols: np.ndarray, noise_std: float) -> np.ndarray:
    """
    Вычисляет LLR для BPSK в AWGN-канале.

    Для отображения:
        0 -> +1
        1 -> -1

    формула:
        LLR = 2 * r / sigma^2
    """
    if noise_std <= 0:
        raise ValueError("noise_std должен быть положительным для вычисления LLR")

    received_symbols = np.asarray(received_symbols, dtype=float)

    return 2.0 * received_symbols / (noise_std ** 2)


def hard_decision_from_llr(llr: np.ndarray) -> np.ndarray:
    """
    Получает жесткое решение из LLR.

    LLR >= 0 -> 0
    LLR < 0  -> 1
    """
    llr = np.asarray(llr, dtype=float)

    return (llr < 0).astype(np.uint8)


def reliability_from_llr(llr: np.ndarray) -> np.ndarray:
    """
    Достоверность символа.

    Чем больше |LLR|, тем выше достоверность.
    Чем ближе LLR к нулю, тем менее надежен бит.
    """
    llr = np.asarray(llr, dtype=float)

    return np.abs(llr)