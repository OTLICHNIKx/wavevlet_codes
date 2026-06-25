import numpy as np


def validate_binary_vector(bits: np.ndarray, name: str = "bits") -> np.ndarray:
    """
    Проверяет, что вектор состоит только из 0 и 1.
    """
    vector = np.asarray(bits, dtype=int).reshape(-1)

    if vector.size == 0:
        raise ValueError(f"{name} не должен быть пустым")

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