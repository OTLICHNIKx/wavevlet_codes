from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Optional

import numpy as np

from decode.chase_decoding import chase_decode
from decode.maximum_likelihood_decoding import build_codebook
from decode.syndrome_decoding import build_syndrome_table, syndrome_decode
from decode.syndrome_decoding.gf2 import solve_gf2, to_binary_matrix
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


def _build_message_recovery_matrix(generator_matrix: np.ndarray) -> np.ndarray:
    """Precompute a GF(2) right inverse that maps codewords back to messages."""
    generator_matrix = to_binary_matrix(generator_matrix, name="generator_matrix")
    k, n = generator_matrix.shape
    recovery = np.zeros((n, k), dtype=np.uint8)
    for message_index in range(k):
        target = np.zeros(k, dtype=np.uint8)
        target[message_index] = 1
        recovery[:, message_index] = solve_gf2(generator_matrix, target)
    if not np.array_equal((generator_matrix @ recovery) % 2, np.eye(k, dtype=np.uint8)):
        raise ValueError("generator_matrix не имеет корректного GF(2) recovery matrix")
    return recovery


def syndrome_decode_batch(
    received_words: np.ndarray,
    parity_check_matrix: np.ndarray,
    generator_matrix: np.ndarray,
    max_error_weight: int,
    syndrome_table: Optional[Mapping[tuple[int, ...], np.ndarray]] = None,
) -> DecoderBatchResult:
    """Векторизованный batch syndrome decoder с одним предвычислением recovery."""
    received_words = _validate_received_words(received_words)
    generator_matrix = to_binary_matrix(generator_matrix, name="generator_matrix")
    parity_check_matrix = to_binary_matrix(parity_check_matrix, name="parity_check_matrix")
    message_count, n = received_words.shape
    k = generator_matrix.shape[0]
    if generator_matrix.shape[1] != n or parity_check_matrix.shape[1] != n:
        raise ValueError("Размерности received_words, G и H должны совпадать по n")
    if syndrome_table is None:
        syndrome_table = build_syndrome_table(
            parity_check_matrix=parity_check_matrix,
            max_error_weight=max_error_weight,
        )

    start_time = perf_counter()
    recovery_matrix = _build_message_recovery_matrix(generator_matrix)
    syndromes = (received_words @ parity_check_matrix.T) % 2
    error_vectors = np.zeros((message_count, n), dtype=np.uint8)
    table_hits = np.zeros(message_count, dtype=bool)
    for index, syndrome in enumerate(syndromes):
        error_vector = syndrome_table.get(tuple(int(value) for value in syndrome))
        if error_vector is not None:
            error_vectors[index] = error_vector
            table_hits[index] = True

    corrected_codewords = (received_words + error_vectors) % 2
    corrected_syndromes = (corrected_codewords @ parity_check_matrix.T) % 2
    success_flags = table_hits & np.all(corrected_syndromes == 0, axis=1)
    decoded_messages = _empty_decoded_messages(message_count, k)
    if np.any(success_flags):
        decoded_messages[success_flags] = (
            corrected_codewords[success_flags] @ recovery_matrix
        ) % 2
    total_time_sec = perf_counter() - start_time
    return DecoderBatchResult(
        decoder_name="syndrome",
        decoded_messages=decoded_messages,
        decoded_codewords=corrected_codewords,
        success_flags=success_flags,
        ambiguous_flags=np.zeros(message_count, dtype=bool),
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
    """Векторизованный Chase: все test patterns декодируются одним syndrome batch."""
    received_words = _validate_received_words(received_words)
    received_symbols = _validate_received_symbols(received_symbols)
    reliability = _validate_reliability(reliability)
    generator_matrix = to_binary_matrix(generator_matrix, name="generator_matrix")
    parity_check_matrix = to_binary_matrix(parity_check_matrix, name="parity_check_matrix")
    if received_words.shape != received_symbols.shape or received_words.shape != reliability.shape:
        raise ValueError("received_words, received_symbols и reliability должны иметь одинаковую форму")
    message_count, n = received_words.shape
    k = generator_matrix.shape[0]
    if unreliable_positions_count <= 0 or unreliable_positions_count > n:
        raise ValueError("unreliable_positions_count должен лежать в диапазоне 1..n")
    if syndrome_table is None:
        syndrome_table = build_syndrome_table(
            parity_check_matrix=parity_check_matrix,
            max_error_weight=inner_decoder_max_error_weight,
        )

    start_time = perf_counter()
    positions = np.argsort(reliability, axis=1, kind="stable")[:, :unreliable_positions_count]
    patterns_count = 1 << unreliable_positions_count
    local_patterns = ((
        np.arange(patterns_count, dtype=np.uint32)[:, None]
        >> np.arange(unreliable_positions_count, dtype=np.uint32)[None, :]
    ) & 1).astype(np.uint8)
    trial_words = np.broadcast_to(
        received_words[:, None, :], (message_count, patterns_count, n)
    ).copy()
    rows = np.arange(message_count)[:, None]
    pattern_indices = np.arange(patterns_count)[None, :]
    for local_index in range(unreliable_positions_count):
        trial_words[rows, pattern_indices, positions[:, local_index, None]] ^= local_patterns[None, :, local_index]

    syndrome_result = syndrome_decode_batch(
        received_words=trial_words.reshape(-1, n),
        parity_check_matrix=parity_check_matrix,
        generator_matrix=generator_matrix,
        max_error_weight=inner_decoder_max_error_weight,
        syndrome_table=syndrome_table,
    )
    candidate_success = syndrome_result.success_flags.reshape(message_count, patterns_count)
    candidate_codewords = syndrome_result.decoded_codewords.reshape(message_count, patterns_count, n)
    candidate_messages = syndrome_result.decoded_messages.reshape(message_count, patterns_count, k)
    modulated = 1.0 - 2.0 * candidate_codewords
    metrics = np.sum((received_symbols[:, None, :] - modulated) ** 2, axis=2)
    metrics[~candidate_success] = np.inf
    best_indices = np.argmin(metrics, axis=1)
    success_flags = np.isfinite(metrics[np.arange(message_count), best_indices])
    decoded_codewords = _empty_decoded_codewords(message_count, n)
    decoded_messages = _empty_decoded_messages(message_count, k)
    decoded_codewords[success_flags] = candidate_codewords[
        np.arange(message_count)[success_flags], best_indices[success_flags]
    ]
    decoded_messages[success_flags] = candidate_messages[
        np.arange(message_count)[success_flags], best_indices[success_flags]
    ]

    ambiguous_flags = np.zeros(message_count, dtype=bool)
    for index in np.flatnonzero(success_flags):
        best_metric = metrics[index, best_indices[index]]
        tied = np.flatnonzero(np.isclose(metrics[index], best_metric))
        unique_codewords = {candidate_codewords[index, candidate].tobytes() for candidate in tied}
        ambiguous_flags[index] = len(unique_codewords) > 1

    total_time_sec = perf_counter() - start_time
    return DecoderBatchResult(
        decoder_name="chase",
        decoded_messages=decoded_messages,
        decoded_codewords=decoded_codewords,
        success_flags=success_flags,
        ambiguous_flags=ambiguous_flags,
        total_time_sec=total_time_sec,
    )
