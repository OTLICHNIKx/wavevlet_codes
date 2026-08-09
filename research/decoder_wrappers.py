from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Optional

import numpy as np

from decode.chase_decoding import chase_decode
from decode.maximum_likelihood_decoding import build_codebook
from decode.syndrome_decoding import build_syndrome_table, syndrome_decode
from decode.syndrome_decoding.gf2 import to_binary_matrix
from modulation.modulator import bpsk_modulate


@dataclass(frozen=True)
class DecoderBatchResult:
    """
    Результат пакетного запуска одного декодера.
    """

    decoder_name: str
    decoded_messages: np.ndarray
    decoded_codewords: np.ndarray
    success_flags: np.ndarray
    ambiguous_flags: np.ndarray
    total_time_sec: float
    skipped: bool = False
    skip_reason: Optional[str] = None


def _empty_decoded_messages(message_count: int, k: int) -> np.ndarray:
    return np.zeros((message_count, k), dtype=np.uint8)


def _empty_decoded_codewords(message_count: int, n: int) -> np.ndarray:
    return np.zeros((message_count, n), dtype=np.uint8)


def _validate_received_words(received_words: np.ndarray) -> np.ndarray:
    received_words = np.asarray(received_words, dtype=np.uint8)

    if received_words.ndim != 2:
        raise ValueError("received_words должен быть двумерной матрицей")

    if not np.all((received_words == 0) | (received_words == 1)):
        raise ValueError("received_words должен содержать только 0 и 1")

    return received_words


def _validate_received_symbols(received_symbols: np.ndarray) -> np.ndarray:
    received_symbols = np.asarray(received_symbols, dtype=float)

    if received_symbols.ndim != 2:
        raise ValueError("received_symbols должен быть двумерной матрицей")

    return received_symbols


def _validate_reliability(reliability: np.ndarray) -> np.ndarray:
    reliability = np.asarray(reliability, dtype=float)

    if reliability.ndim != 2:
        raise ValueError("reliability должен быть двумерной матрицей")

    return reliability


def syndrome_decode_batch(
    received_words: np.ndarray,
    parity_check_matrix: np.ndarray,
    generator_matrix: np.ndarray,
    max_error_weight: int,
    syndrome_table: Optional[Mapping[tuple[int, ...], np.ndarray]] = None,
) -> DecoderBatchResult:
    """
    Пакетный запуск синдромного декодера.
    """
    received_words = _validate_received_words(received_words)

    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    parity_check_matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    message_count, n = received_words.shape
    k = generator_matrix.shape[0]

    decoded_messages = _empty_decoded_messages(message_count, k)
    decoded_codewords = _empty_decoded_codewords(message_count, n)
    success_flags = np.zeros(message_count, dtype=bool)
    ambiguous_flags = np.zeros(message_count, dtype=bool)

    if syndrome_table is None:
        syndrome_table = build_syndrome_table(
            parity_check_matrix=parity_check_matrix,
            max_error_weight=max_error_weight,
        )

    start_time = perf_counter()

    for index, received_word in enumerate(received_words):
        result = syndrome_decode(
            received_word=received_word,
            parity_check_matrix=parity_check_matrix,
            generator_matrix=generator_matrix,
            syndrome_table=syndrome_table,
            max_error_weight=max_error_weight,
        )

        success_flags[index] = result.success
        decoded_codewords[index] = result.corrected_word

        if result.decoded_message is not None:
            decoded_messages[index] = result.decoded_message

    total_time_sec = perf_counter() - start_time

    return DecoderBatchResult(
        decoder_name="syndrome",
        decoded_messages=decoded_messages,
        decoded_codewords=decoded_codewords,
        success_flags=success_flags,
        ambiguous_flags=ambiguous_flags,
        total_time_sec=total_time_sec,
    )


def hard_mld_decode_batch(
    received_words: np.ndarray,
    generator_matrix: np.ndarray,
    chunk_size: int = 128,
) -> DecoderBatchResult:
    """
    Пакетный Hard MLD.

    Метрика:
        расстояние Хэмминга.
    """
    received_words = _validate_received_words(received_words)

    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    if chunk_size <= 0:
        raise ValueError("chunk_size должен быть положительным")

    messages, codewords = build_codebook(generator_matrix)

    message_count, n = received_words.shape
    k = generator_matrix.shape[0]

    decoded_messages = _empty_decoded_messages(message_count, k)
    decoded_codewords = _empty_decoded_codewords(message_count, n)
    success_flags = np.ones(message_count, dtype=bool)
    ambiguous_flags = np.zeros(message_count, dtype=bool)

    start_time = perf_counter()

    for start in range(0, message_count, chunk_size):
        end = min(start + chunk_size, message_count)
        received_chunk = received_words[start:end]

        distances = np.sum(
            codewords[None, :, :] != received_chunk[:, None, :],
            axis=2,
        )

        best_indices = np.argmin(distances, axis=1)
        best_distances = distances[np.arange(end - start), best_indices]

        decoded_messages[start:end] = messages[best_indices]
        decoded_codewords[start:end] = codewords[best_indices]

        ambiguous_flags[start:end] = np.sum(
            distances == best_distances[:, None],
            axis=1,
        ) > 1

    total_time_sec = perf_counter() - start_time

    return DecoderBatchResult(
        decoder_name="hard_mld",
        decoded_messages=decoded_messages,
        decoded_codewords=decoded_codewords,
        success_flags=success_flags,
        ambiguous_flags=ambiguous_flags,
        total_time_sec=total_time_sec,
    )


def soft_mld_decode_batch(
    received_symbols: np.ndarray,
    generator_matrix: np.ndarray,
    chunk_size: int = 128,
) -> DecoderBatchResult:
    """
    Пакетный Soft MLD для BPSK + AWGN.

    Минимизация евклидовой метрики эквивалентна максимизации:
        received_symbols @ modulated_codeword
    """
    received_symbols = _validate_received_symbols(received_symbols)

    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    if chunk_size <= 0:
        raise ValueError("chunk_size должен быть положительным")

    messages, codewords = build_codebook(generator_matrix)

    modulated_codewords = np.asarray(
        [bpsk_modulate(codeword) for codeword in codewords],
        dtype=float,
    )

    message_count, n = received_symbols.shape
    k = generator_matrix.shape[0]

    decoded_messages = _empty_decoded_messages(message_count, k)
    decoded_codewords = _empty_decoded_codewords(message_count, n)
    success_flags = np.ones(message_count, dtype=bool)
    ambiguous_flags = np.zeros(message_count, dtype=bool)

    start_time = perf_counter()

    for start in range(0, message_count, chunk_size):
        end = min(start + chunk_size, message_count)
        received_chunk = received_symbols[start:end]

        scores = received_chunk @ modulated_codewords.T

        best_indices = np.argmax(scores, axis=1)
        best_scores = scores[np.arange(end - start), best_indices]

        decoded_messages[start:end] = messages[best_indices]
        decoded_codewords[start:end] = codewords[best_indices]

        ambiguous_flags[start:end] = np.sum(
            np.isclose(scores, best_scores[:, None]),
            axis=1,
        ) > 1

    total_time_sec = perf_counter() - start_time

    return DecoderBatchResult(
        decoder_name="soft_mld",
        decoded_messages=decoded_messages,
        decoded_codewords=decoded_codewords,
        success_flags=success_flags,
        ambiguous_flags=ambiguous_flags,
        total_time_sec=total_time_sec,
    )


def chase_decode_batch(
    received_words: np.ndarray,
    received_symbols: np.ndarray,
    reliability: np.ndarray,
    parity_check_matrix: np.ndarray,
    generator_matrix: np.ndarray,
    unreliable_positions_count: int,
    inner_decoder_max_error_weight: int,
    syndrome_table: Optional[Mapping[tuple[int, ...], np.ndarray]] = None,
) -> DecoderBatchResult:
    """
    Пакетный запуск алгоритма Чейза.
    """
    received_words = _validate_received_words(received_words)
    received_symbols = _validate_received_symbols(received_symbols)
    reliability = _validate_reliability(reliability)

    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    parity_check_matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    if received_words.shape != received_symbols.shape:
        raise ValueError("received_words и received_symbols должны иметь одинаковую форму")

    if received_words.shape != reliability.shape:
        raise ValueError("received_words и reliability должны иметь одинаковую форму")

    message_count, n = received_words.shape
    k = generator_matrix.shape[0]

    decoded_messages = _empty_decoded_messages(message_count, k)
    decoded_codewords = _empty_decoded_codewords(message_count, n)
    success_flags = np.zeros(message_count, dtype=bool)
    ambiguous_flags = np.zeros(message_count, dtype=bool)

    if syndrome_table is None:
        syndrome_table = build_syndrome_table(
            parity_check_matrix=parity_check_matrix,
            max_error_weight=inner_decoder_max_error_weight,
        )

    start_time = perf_counter()

    for index in range(message_count):
        result = chase_decode(
            received_word=received_words[index],
            received_symbols=received_symbols[index],
            reliability=reliability[index],
            parity_check_matrix=parity_check_matrix,
            generator_matrix=generator_matrix,
            unreliable_positions_count=unreliable_positions_count,
            inner_decoder_max_error_weight=inner_decoder_max_error_weight,
            syndrome_table=syndrome_table,
        )

        success_flags[index] = result.success
        ambiguous_flags[index] = result.ambiguous

        if result.decoded_codeword is not None:
            decoded_codewords[index] = result.decoded_codeword

        if result.decoded_message is not None:
            decoded_messages[index] = result.decoded_message

    total_time_sec = perf_counter() - start_time

    return DecoderBatchResult(
        decoder_name="chase",
        decoded_messages=decoded_messages,
        decoded_codewords=decoded_codewords,
        success_flags=success_flags,
        ambiguous_flags=ambiguous_flags,
        total_time_sec=total_time_sec,
    )