import numpy as np


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