from dataclasses import dataclass
from itertools import combinations
from typing import Optional

import numpy as np

from .gf2 import solve_gf2, to_binary_matrix, to_binary_vector


@dataclass
class SyndromeDecodingResult:
    """
    Результат синдромного декодирования.
    """

    received_word: np.ndarray
    syndrome: np.ndarray
    error_vector: np.ndarray
    corrected_word: np.ndarray
    decoded_message: Optional[np.ndarray]
    success: bool
    message: str


def calculate_syndrome(
    received_word: np.ndarray,
    parity_check_matrix: np.ndarray,
) -> np.ndarray:
    """
    Вычисляет синдром:
        s = received_word @ H.T
    """
    received_word = to_binary_vector(received_word, name="received_word")
    parity_check_matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    if parity_check_matrix.shape[1] != len(received_word):
        raise ValueError(
            "Количество столбцов проверочной матрицы должно совпадать "
            "с длиной принятого слова"
        )

    return (received_word @ parity_check_matrix.T) % 2


def hamming_weight(vector: np.ndarray) -> int:
    """
    Вес Хэмминга — количество единиц в векторе.
    """
    vector = to_binary_vector(vector, name="vector")
    return int(np.sum(vector))


def build_syndrome_table(
    parity_check_matrix: np.ndarray,
    max_error_weight: int = 1,
) -> dict[tuple[int, ...], np.ndarray]:
    """
    Строит таблицу синдромов.

    Каждому синдрому сопоставляется ошибка минимального веса
    среди ошибок веса не больше max_error_weight.
    """
    parity_check_matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    if max_error_weight < 0:
        raise ValueError("max_error_weight должен быть неотрицательным")

    codeword_length = parity_check_matrix.shape[1]
    syndrome_table: dict[tuple[int, ...], np.ndarray] = {}

    for weight in range(max_error_weight + 1):
        for positions in combinations(range(codeword_length), weight):
            error_vector = np.zeros(codeword_length, dtype=np.uint8)

            for position in positions:
                error_vector[position] = 1

            syndrome = calculate_syndrome(
                received_word=error_vector,
                parity_check_matrix=parity_check_matrix,
            )

            syndrome_key = tuple(int(value) for value in syndrome)

            if syndrome_key not in syndrome_table:
                syndrome_table[syndrome_key] = error_vector

    return syndrome_table


def recover_message_from_codeword(
    corrected_word: np.ndarray,
    generator_matrix: np.ndarray,
) -> np.ndarray:
    """
    Восстанавливает информационное слово v из кодового слова c.

    У нас кодирование выполняется так:
        c = v @ G

    Поэтому решаем систему:
        G.T @ v.T = c.T
    """
    corrected_word = to_binary_vector(corrected_word, name="corrected_word")
    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    if generator_matrix.shape[1] != len(corrected_word):
        raise ValueError(
            "Количество столбцов порождающей матрицы должно совпадать "
            "с длиной исправленного слова"
        )

    return solve_gf2(
        matrix=generator_matrix.T,
        vector=corrected_word,
    )


def syndrome_decode(
    received_word: np.ndarray,
    parity_check_matrix: np.ndarray,
    generator_matrix: Optional[np.ndarray] = None,
    syndrome_table: Optional[dict[tuple[int, ...], np.ndarray]] = None,
    max_error_weight: int = 1,
) -> SyndromeDecodingResult:
    """
    Выполняет синдромное декодирование.

    Алгоритм:
        1. Вычислить синдром s.
        2. Найти ошибку e_hat по таблице синдромов.
        3. Исправить слово: c_hat = y + e_hat.
        4. Проверить, что синдром исправленного слова равен нулю.
        5. Если задана G, восстановить информационное сообщение.
    """
    received_word = to_binary_vector(received_word, name="received_word")
    parity_check_matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    if syndrome_table is None:
        syndrome_table = build_syndrome_table(
            parity_check_matrix=parity_check_matrix,
            max_error_weight=max_error_weight,
        )

    syndrome = calculate_syndrome(
        received_word=received_word,
        parity_check_matrix=parity_check_matrix,
    )

    syndrome_key = tuple(int(value) for value in syndrome)

    if syndrome_key not in syndrome_table:
        return SyndromeDecodingResult(
            received_word=received_word,
            syndrome=syndrome,
            error_vector=np.zeros_like(received_word),
            corrected_word=received_word.copy(),
            decoded_message=None,
            success=False,
            message=(
                "Синдром отсутствует в таблице. "
                "Ошибка не исправлена при заданном max_error_weight."
            ),
        )

    error_vector = syndrome_table[syndrome_key]
    corrected_word = (received_word + error_vector) % 2

    check_syndrome = calculate_syndrome(
        received_word=corrected_word,
        parity_check_matrix=parity_check_matrix,
    )

    if not np.all(check_syndrome == 0):
        return SyndromeDecodingResult(
            received_word=received_word,
            syndrome=syndrome,
            error_vector=error_vector,
            corrected_word=corrected_word,
            decoded_message=None,
            success=False,
            message="После исправления синдром не стал нулевым.",
        )

    decoded_message = None

    if generator_matrix is not None:
        decoded_message = recover_message_from_codeword(
            corrected_word=corrected_word,
            generator_matrix=generator_matrix,
        )

    return SyndromeDecodingResult(
        received_word=received_word,
        syndrome=syndrome,
        error_vector=error_vector,
        corrected_word=corrected_word,
        decoded_message=decoded_message,
        success=True,
        message="Синдромное декодирование выполнено успешно.",
    )