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


def bpsk_llr_with_gain(
    received_symbols: np.ndarray,
    noise_std: float,
    channel_gain: np.ndarray,
) -> np.ndarray:
    """
    LLR для BPSK с известным коэффициентом канала (замирания).

    Для r = h*x + n:
        LLR = 2 * h * r / sigma^2

    channel_gain может быть:
    - скаляром (одинаковое замирание для всех символов)
    - массивом той же формы, что received_symbols (частное замирание)
    """
    if noise_std <= 0:
        raise ValueError("noise_std должен быть положительным")

    received_symbols = np.asarray(received_symbols, dtype=float)
    channel_gain = np.asarray(channel_gain, dtype=float)

    if channel_gain.shape != received_symbols.shape:
        # broadcast (n,) или (n, 1) -> (n, m)
        if channel_gain.size == 1:
            channel_gain = np.broadcast_to(channel_gain, received_symbols.shape)
        elif channel_gain.ndim == 1:
            # (n,) -> (n, 1) -> broadcast to (n, m)
            channel_gain = channel_gain.reshape((channel_gain.shape[0], 1))
            channel_gain = np.broadcast_to(channel_gain, received_symbols.shape)
        elif channel_gain.ndim == 2 and channel_gain.shape[1] == 1:
            # (n, 1) -> broadcast to (n, m)
            channel_gain = np.broadcast_to(channel_gain, received_symbols.shape)
        else:
            raise ValueError(
                f"channel_gain shape {channel_gain.shape} не совместим с "
                f"received_symbols {received_symbols.shape}"
            )

    return 2.0 * channel_gain * received_symbols / (noise_std ** 2)


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