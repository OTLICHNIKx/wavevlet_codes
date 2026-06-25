from dataclasses import dataclass
from itertools import product
from typing import Optional

import numpy as np

from decode.syndrome_decoding.gf2 import to_binary_matrix, to_binary_vector
from modulation.modulator import bpsk_modulate


@dataclass
class MaximumLikelihoodDecodingResult:
    """
    Результат декодирования методом максимального правдоподобия.
    """

    decoded_message: np.ndarray
    decoded_codeword: np.ndarray
    metric: float
    metric_name: str
    candidates_count: int
    best_candidates_count: int
    ambiguous: bool
    success: bool
    message: str
    received_word: Optional[np.ndarray] = None
    received_symbols: Optional[np.ndarray] = None


def generate_all_binary_messages(k: int, max_candidates: int = 1_000_000) -> np.ndarray:
    """
    Генерирует все информационные слова длины k.

    Количество вариантов:
        2^k
    """
    if k <= 0:
        raise ValueError("k должно быть положительным")

    candidates_count = 2 ** k

    if candidates_count > max_candidates:
        raise ValueError(
            f"Слишком много кандидатов для полного перебора: 2^{k} = {candidates_count}. "
            f"Текущий предел: {max_candidates}."
        )

    return np.asarray(
        list(product([0, 1], repeat=k)),
        dtype=np.uint8,
    )


def build_codebook(generator_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Строит все кодовые слова кода.

    Возвращает:
        messages — все информационные слова
        codewords — соответствующие кодовые слова
    """
    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    k = generator_matrix.shape[0]
    messages = generate_all_binary_messages(k)
    codewords = (messages @ generator_matrix) % 2

    return messages, codewords.astype(np.uint8)


def hamming_distance_batch(codewords: np.ndarray, received_word: np.ndarray) -> np.ndarray:
    """
    Считает расстояние Хэмминга от каждого кодового слова до принятого слова.
    """
    received_word = to_binary_vector(received_word, name="received_word")
    codewords = to_binary_matrix(codewords, name="codewords")

    if codewords.shape[1] != len(received_word):
        raise ValueError(
            "Длина принятого слова должна совпадать с длиной кодовых слов"
        )

    return np.sum(codewords != received_word, axis=1)


def euclidean_metric_batch(codewords: np.ndarray, received_symbols: np.ndarray) -> np.ndarray:
    """
    Считает евклидову метрику для BPSK/AWGN.

    Каждое кодовое слово сначала модулируется:
        0 -> +1
        1 -> -1

    Затем считаем:
        sum((r_i - s_i)^2)
    """
    received_symbols = np.asarray(received_symbols, dtype=float).reshape(-1)
    codewords = to_binary_matrix(codewords, name="codewords")

    if codewords.shape[1] != len(received_symbols):
        raise ValueError(
            "Длина принятого сигнального вектора должна совпадать с длиной кодовых слов"
        )

    modulated_codewords = np.asarray(
        [bpsk_modulate(codeword) for codeword in codewords],
        dtype=float,
    )

    differences = modulated_codewords - received_symbols

    return np.sum(differences ** 2, axis=1)


def hard_maximum_likelihood_decode(
    received_word: np.ndarray,
    generator_matrix: np.ndarray,
) -> MaximumLikelihoodDecodingResult:
    """
    Жёсткое MLD.

    Выбирает кодовое слово с минимальным расстоянием Хэмминга
    до принятого жёсткого слова.
    """
    received_word = to_binary_vector(received_word, name="received_word")

    messages, codewords = build_codebook(generator_matrix)

    distances = hamming_distance_batch(
        codewords=codewords,
        received_word=received_word,
    )

    best_metric = int(np.min(distances))
    best_indices = np.where(distances == best_metric)[0]
    best_index = int(best_indices[0])

    ambiguous = len(best_indices) > 1

    return MaximumLikelihoodDecodingResult(
        received_word=received_word,
        received_symbols=None,
        decoded_message=messages[best_index],
        decoded_codeword=codewords[best_index],
        metric=float(best_metric),
        metric_name="Hamming distance",
        candidates_count=len(codewords),
        best_candidates_count=len(best_indices),
        ambiguous=ambiguous,
        success=True,
        message=(
            "Hard MLD выполнено успешно."
            if not ambiguous
            else "Hard MLD выполнено, но есть несколько кодовых слов с одинаковой минимальной метрикой."
        ),
    )


def soft_maximum_likelihood_decode(
    received_symbols: np.ndarray,
    generator_matrix: np.ndarray,
) -> MaximumLikelihoodDecodingResult:
    """
    Мягкое MLD для BPSK/AWGN.

    Выбирает кодовое слово, BPSK-образ которого ближе всего
    к принятому вещественному вектору.
    """
    received_symbols = np.asarray(received_symbols, dtype=float).reshape(-1)

    messages, codewords = build_codebook(generator_matrix)

    metrics = euclidean_metric_batch(
        codewords=codewords,
        received_symbols=received_symbols,
    )

    best_metric = float(np.min(metrics))
    best_indices = np.where(np.isclose(metrics, best_metric))[0]
    best_index = int(best_indices[0])

    ambiguous = len(best_indices) > 1

    return MaximumLikelihoodDecodingResult(
        received_word=None,
        received_symbols=received_symbols,
        decoded_message=messages[best_index],
        decoded_codeword=codewords[best_index],
        metric=best_metric,
        metric_name="Euclidean metric",
        candidates_count=len(codewords),
        best_candidates_count=len(best_indices),
        ambiguous=ambiguous,
        success=True,
        message=(
            "Soft MLD выполнено успешно."
            if not ambiguous
            else "Soft MLD выполнено, но есть несколько кодовых слов с одинаковой минимальной метрикой."
        ),
    )