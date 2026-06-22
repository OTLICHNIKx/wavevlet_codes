from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np


def to_binary_vector(values: Iterable[int], name: str = "vector") -> np.ndarray:
    """
    Преобразует входные данные в бинарный вектор над GF(2).
    """
    vector = np.array(list(values), dtype=int).reshape(-1)

    if not np.all((vector == 0) | (vector == 1)):
        raise ValueError(f"{name} должен содержать только 0 и 1")

    return vector.astype(np.uint8)


def to_binary_matrix(values: Iterable[Iterable[int]], name: str = "matrix") -> np.ndarray:
    """
    Преобразует входные данные в бинарную матрицу над GF(2).
    """
    matrix = np.array(values, dtype=int)

    if matrix.ndim != 2:
        raise ValueError(f"{name} должна быть двумерной матрицей")

    if not np.all((matrix == 0) | (matrix == 1)):
        raise ValueError(f"{name} должна содержать только 0 и 1")

    return matrix.astype(np.uint8)


def gf2_matmul(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """
    Умножение матриц/векторов над GF(2).
    """
    return (left @ right) % 2


@dataclass
class WaveletCode:
    """
    Линейный вейвлетный код, заданный порождающей матрицей.

    Используем соглашение:
        G имеет размер k x n
        message имеет длину k
        codeword = message @ G mod 2
    """

    generator_matrix: np.ndarray
    name: str = "Binary wavelet code"
    check_matrix: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        self.generator_matrix = to_binary_matrix(
            self.generator_matrix,
            name="generator_matrix"
        )

        if self.check_matrix is not None:
            self.check_matrix = to_binary_matrix(
                self.check_matrix,
                name="check_matrix"
            )

            if self.check_matrix.shape[1] != self.n:
                raise ValueError(
                    "Проверочная матрица должна иметь столько же столбцов, "
                    "сколько длина кодового слова n"
                )

            product = gf2_matmul(self.check_matrix, self.generator_matrix.T)

            if not np.all(product == 0):
                raise ValueError(
                    "Матрицы G и H несогласованы: H @ G.T должно быть равно 0"
                )

    @property
    def k(self) -> int:
        """
        Длина информационного сообщения.
        """
        return self.generator_matrix.shape[0]

    @property
    def n(self) -> int:
        """
        Длина кодового слова.
        """
        return self.generator_matrix.shape[1]

    def encode(self, message: Iterable[int]) -> np.ndarray:
        """
        Кодирует информационное сообщение.

        message: бинарный вектор длины k
        return: кодовое слово длины n
        """
        message_vector = to_binary_vector(message, name="message")

        if len(message_vector) != self.k:
            raise ValueError(
                f"Длина сообщения должна быть k = {self.k}, "
                f"получено {len(message_vector)}"
            )

        codeword = gf2_matmul(message_vector, self.generator_matrix)
        return codeword.astype(np.uint8)

    def syndrome(self, word: Iterable[int]) -> np.ndarray:
        """
        Вычисляет синдром слова.

        Используется позже для проверки/декодирования.
        """
        if self.check_matrix is None:
            raise ValueError("Проверочная матрица H не задана")

        word_vector = to_binary_vector(word, name="word")

        if len(word_vector) != self.n:
            raise ValueError(
                f"Длина слова должна быть n = {self.n}, "
                f"получено {len(word_vector)}"
            )

        return gf2_matmul(self.check_matrix, word_vector.T)