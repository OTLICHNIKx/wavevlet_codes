from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product
from typing import Optional

import numpy as np

from decode.syndrome_decoding import syndrome_decode
from decode.syndrome_decoding.gf2 import to_binary_matrix, to_binary_vector
from modulation.modulator import bpsk_modulate


@dataclass
class ChaseCandidate:
    """
    Один кандидат алгоритма Чейза.
    """

    test_pattern: np.ndarray
    trial_word: np.ndarray
    decoded_codeword: np.ndarray
    decoded_message: Optional[np.ndarray]
    metric: float


@dataclass
class ChaseDecodingResult:
    """
    Результат декодирования алгоритмом Чейза.
    """

    received_word: np.ndarray
    received_symbols: np.ndarray
    reliability: np.ndarray
    unreliable_positions: np.ndarray
    decoded_codeword: Optional[np.ndarray]
    decoded_message: Optional[np.ndarray]
    metric: Optional[float]
    candidates_count: int
    best_candidates_count: int
    ambiguous: bool
    success: bool
    message: str
    candidates: list[ChaseCandidate]


def select_least_reliable_positions(
    reliability: np.ndarray,
    positions_count: int,
) -> np.ndarray:
    """
    Выбирает positions_count наименее надёжных позиций.

    Чем меньше reliability[i], тем менее надёжен символ.
    """
    reliability = np.asarray(reliability, dtype=float).reshape(-1)

    if positions_count <= 0:
        raise ValueError("positions_count должно быть положительным")

    if positions_count > len(reliability):
        raise ValueError(
            "Количество ненадёжных позиций не может быть больше длины слова"
        )

    return np.argsort(reliability)[:positions_count]


def build_test_patterns(
    codeword_length: int,
    unreliable_positions: np.ndarray,
) -> list[np.ndarray]:
    """
    Строит все тестовые шаблоны ошибок.

    Единицы могут стоять только в наименее надёжных позициях.
    Если выбрано p позиций, будет 2^p шаблонов.
    """
    unreliable_positions = np.asarray(unreliable_positions, dtype=int).reshape(-1)
    patterns = []

    for bits in product([0, 1], repeat=len(unreliable_positions)):
        pattern = np.zeros(codeword_length, dtype=np.uint8)

        for position, bit in zip(unreliable_positions, bits):
            pattern[position] = bit

        patterns.append(pattern)

    return patterns


def euclidean_metric_for_codeword(
    codeword: np.ndarray,
    received_symbols: np.ndarray,
) -> float:
    """
    Евклидова метрика для BPSK/AWGN.

    Чем меньше метрика, тем правдоподобнее кодовое слово.
    """
    codeword = to_binary_vector(codeword, name="codeword")
    received_symbols = np.asarray(received_symbols, dtype=float).reshape(-1)

    if len(codeword) != len(received_symbols):
        raise ValueError(
            "Длина кодового слова должна совпадать с длиной принятого сигнального вектора"
        )

    modulated_codeword = bpsk_modulate(codeword)
    difference = received_symbols - modulated_codeword

    return float(np.sum(difference ** 2))


def chase_decode(
    received_word: np.ndarray,
    received_symbols: np.ndarray,
    reliability: np.ndarray,
    parity_check_matrix: np.ndarray,
    generator_matrix: np.ndarray,
    unreliable_positions_count: int = 2,
    inner_decoder_max_error_weight: int = 1,
    syndrome_table: Optional[Mapping[tuple[int, ...], np.ndarray]] = None,
) -> ChaseDecodingResult:
    """
    Алгоритм Чейза.

    Шаги:
        1. Выбрать p наименее надёжных позиций.
        2. Построить 2^p тестовых шаблонов.
        3. Для каждого шаблона инвертировать соответствующие биты.
        4. Прогнать пробное слово через жёсткий синдромный декодер.
        5. Удалить дубликаты кодовых слов.
        6. Выбрать кандидата с минимальной евклидовой метрикой.
    """
    received_word = to_binary_vector(received_word, name="received_word")
    received_symbols = np.asarray(received_symbols, dtype=float).reshape(-1)
    reliability = np.asarray(reliability, dtype=float).reshape(-1)

    parity_check_matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    generator_matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    if len(received_word) != len(received_symbols):
        raise ValueError(
            "Длина received_word должна совпадать с длиной received_symbols"
        )

    if len(received_word) != len(reliability):
        raise ValueError(
            "Длина received_word должна совпадать с длиной reliability"
        )

    unreliable_positions = select_least_reliable_positions(
        reliability=reliability,
        positions_count=unreliable_positions_count,
    )

    test_patterns = build_test_patterns(
        codeword_length=len(received_word),
        unreliable_positions=unreliable_positions,
    )

    candidates_by_codeword: dict[tuple[int, ...], ChaseCandidate] = {}

    for test_pattern in test_patterns:
        trial_word = (received_word + test_pattern) % 2

        syndrome_result = syndrome_decode(
            received_word=trial_word,
            parity_check_matrix=parity_check_matrix,
            generator_matrix=generator_matrix,
            syndrome_table=syndrome_table,
            max_error_weight=inner_decoder_max_error_weight,
        )

        if not syndrome_result.success:
            continue

        decoded_codeword = syndrome_result.corrected_word
        codeword_key = tuple(int(value) for value in decoded_codeword)

        if codeword_key in candidates_by_codeword:
            continue

        metric = euclidean_metric_for_codeword(
            codeword=decoded_codeword,
            received_symbols=received_symbols,
        )

        candidates_by_codeword[codeword_key] = ChaseCandidate(
            test_pattern=test_pattern,
            trial_word=trial_word,
            decoded_codeword=decoded_codeword,
            decoded_message=syndrome_result.decoded_message,
            metric=metric,
        )

    candidates = list(candidates_by_codeword.values())

    if not candidates:
        return ChaseDecodingResult(
            received_word=received_word,
            received_symbols=received_symbols,
            reliability=reliability,
            unreliable_positions=unreliable_positions,
            decoded_codeword=None,
            decoded_message=None,
            metric=None,
            candidates_count=0,
            best_candidates_count=0,
            ambiguous=False,
            success=False,
            message="Алгоритм Чейза не получил ни одного успешного кандидата.",
            candidates=[],
        )

    metrics = np.asarray([candidate.metric for candidate in candidates], dtype=float)
    best_metric = float(np.min(metrics))
    best_indices = np.where(np.isclose(metrics, best_metric))[0]
    best_index = int(best_indices[0])
    best_candidate = candidates[best_index]

    ambiguous = len(best_indices) > 1

    return ChaseDecodingResult(
        received_word=received_word,
        received_symbols=received_symbols,
        reliability=reliability,
        unreliable_positions=unreliable_positions,
        decoded_codeword=best_candidate.decoded_codeword,
        decoded_message=best_candidate.decoded_message,
        metric=best_candidate.metric,
        candidates_count=len(candidates),
        best_candidates_count=len(best_indices),
        ambiguous=ambiguous,
        success=True,
        message=(
            "Алгоритм Чейза выполнен успешно."
            if not ambiguous
            else "Алгоритм Чейза выполнен, но есть несколько кандидатов с одинаковой метрикой."
        ),
        candidates=candidates,
    )