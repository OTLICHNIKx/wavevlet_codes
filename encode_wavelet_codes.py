from typing import Iterable, Tuple

import numpy as np

from wavelet_codes import WaveletCode


FIELD = 2


def ensure_binary_vector(values: Iterable[int], name: str = "vector") -> np.ndarray:
    """
    Проверяет, что вход является бинарным вектором.
    """
    vector = np.asarray(list(values), dtype=int).reshape(-1)

    if vector.size == 0:
        raise ValueError(f"{name} не должен быть пустым")

    if not np.all((vector == 0) | (vector == 1)):
        raise ValueError(f"{name} должен содержать только 0 и 1")

    return vector.astype(np.uint8)


def build_wavelet_code_for_message(
    h: Iterable[int],
    message: Iterable[int],
    a: int = 1,
    shift: int = 1,
) -> WaveletCode:
    """
    Строит бинарный линейный вейвлетный код под длину сообщения.

    Для нашей схемы:
        k = len(message)
        n = 2k
    """
    h_vector = ensure_binary_vector(h, name="h")
    message_vector = ensure_binary_vector(message, name="message")

    if len(h_vector) % 2 != 0:
        raise ValueError("Количество коэффициентов h должно быть чётным")

    codeword_length = 2 * len(message_vector)

    if len(h_vector) > codeword_length:
        raise ValueError(
            "Количество коэффициентов h не может быть больше длины кодового слова: "
            f"len(h) = {len(h_vector)}, n = {codeword_length}"
        )

    return WaveletCode.from_scaling_coefficients(
        h=h_vector,
        codeword_length=codeword_length,
        field=FIELD,
        a=a,
        shift=shift,
        name="Binary wavelet code",
    )


def encode_wavelet_message(
    h: Iterable[int],
    message: Iterable[int],
    a: int = 1,
    shift: int = 1,
) -> Tuple[WaveletCode, np.ndarray]:
    """
    Строит код и кодирует информационное сообщение.

    Возвращает:
        code — объект WaveletCode
        codeword — кодовое слово
    """
    message_vector = ensure_binary_vector(message, name="message")

    code = build_wavelet_code_for_message(
        h=h,
        message=message_vector,
        a=a,
        shift=shift,
    )

    codeword = code.encode(message_vector)

    return code, codeword