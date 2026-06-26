from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class BatchMetrics:
    """
    Метрики одного пакетного запуска декодера.

    total_messages:
        количество переданных сообщений

    bit_errors:
        количество ошибочных информационных битов

    ber:
        bit error rate по информационным битам

    packet_errors:
        количество ошибочных пакетов по информационным сообщениям

    packet_error_rate:
        доля сообщений, восстановленных с ошибкой

    codeword_packet_errors:
        количество ошибочных пакетов по кодовым словам

    codeword_packet_error_rate:
        доля кодовых слов, восстановленных с ошибкой

    failure_rate:
        доля случаев, когда декодер не вернул успешный результат

    ambiguous_rate:
        доля неоднозначных решений

    avg_time_ms:
        среднее время декодирования одного сообщения
    """

    total_messages: int

    bit_errors: int
    total_bits: int
    ber: float

    packet_errors: int
    packet_error_rate: float

    frame_errors: int
    frame_error_rate: float

    codeword_packet_errors: Optional[int]
    codeword_packet_error_rate: Optional[float]

    failure_count: int
    failure_rate: float

    ambiguous_count: int
    ambiguous_rate: float

    total_time_sec: float
    avg_time_ms: float


def _to_2d_array(values: np.ndarray, name: str) -> np.ndarray:
    """
    Приводит вход к двумерному массиву.
    """
    array = np.asarray(values)

    if array.ndim != 2:
        raise ValueError(f"{name} должен быть двумерным массивом")

    if array.shape[0] == 0:
        raise ValueError(f"{name} не должен быть пустым")

    return array


def _to_bool_flags(
    flags: Optional[np.ndarray],
    length: int,
    default: bool,
    name: str,
) -> np.ndarray:
    """
    Приводит флаги к булевому вектору нужной длины.
    """
    if flags is None:
        return np.full(length, default, dtype=bool)

    flags = np.asarray(flags, dtype=bool).reshape(-1)

    if len(flags) != length:
        raise ValueError(f"{name} должен иметь длину {length}")

    return flags


def bit_error_rate(
    original_messages: np.ndarray,
    decoded_messages: np.ndarray,
    success_flags: Optional[np.ndarray] = None,
    count_failure_as_full_error: bool = True,
) -> float:
    """
    BER по информационным сообщениям.

    Если count_failure_as_full_error=True, то неуспешное декодирование
    считается ошибкой во всех k битах сообщения.
    """
    original_messages = _to_2d_array(original_messages, "original_messages")
    decoded_messages = _to_2d_array(decoded_messages, "decoded_messages")

    if original_messages.shape != decoded_messages.shape:
        raise ValueError("original_messages и decoded_messages должны иметь одинаковую форму")

    message_count, message_length = original_messages.shape

    success_flags = _to_bool_flags(
        flags=success_flags,
        length=message_count,
        default=True,
        name="success_flags",
    )

    bit_errors_by_row = np.sum(original_messages != decoded_messages, axis=1)

    if count_failure_as_full_error:
        bit_errors_by_row = bit_errors_by_row.astype(int)
        bit_errors_by_row[~success_flags] = message_length

    total_errors = int(np.sum(bit_errors_by_row))
    total_bits = int(message_count * message_length)

    return float(total_errors / total_bits)


def packet_error_rate(
    original_messages: np.ndarray,
    decoded_messages: np.ndarray,
    success_flags: Optional[np.ndarray] = None,
) -> float:
    """
    PER / FER по информационным сообщениям.

    Пакет считается ошибочным, если:
        1. decoded_message отличается от original_message;
        2. декодер завершился неуспешно.
    """
    original_messages = _to_2d_array(original_messages, "original_messages")
    decoded_messages = _to_2d_array(decoded_messages, "decoded_messages")

    if original_messages.shape != decoded_messages.shape:
        raise ValueError("original_messages и decoded_messages должны иметь одинаковую форму")

    message_count = original_messages.shape[0]

    success_flags = _to_bool_flags(
        flags=success_flags,
        length=message_count,
        default=True,
        name="success_flags",
    )

    message_errors = np.any(original_messages != decoded_messages, axis=1)
    packet_errors = np.logical_or(message_errors, ~success_flags)

    return float(np.mean(packet_errors))

def frame_error_rate(
    original_messages: np.ndarray,
    decoded_messages: np.ndarray,
    success_flags: Optional[np.ndarray] = None,
) -> float:
    """
    FER = Frame Error Rate.

    В нашем исследовании один frame — это одно информационное сообщение.

    Frame считается ошибочным, если:
        1. decoded_message отличается от original_message;
        2. декодер завершился неуспешно.

    Сейчас FER совпадает с packet_error_rate, но оставляем отдельную функцию,
    чтобы в итоговой таблице была стандартная метрика FER.
    """
    return packet_error_rate(
        original_messages=original_messages,
        decoded_messages=decoded_messages,
        success_flags=success_flags,
    )

def codeword_packet_error_rate(
    original_codewords: np.ndarray,
    decoded_codewords: np.ndarray,
    success_flags: Optional[np.ndarray] = None,
) -> float:
    """
    Пакетная ошибка по кодовым словам.

    Пакет считается ошибочным, если:
        1. decoded_codeword отличается от original_codeword;
        2. декодер завершился неуспешно.
    """
    original_codewords = _to_2d_array(original_codewords, "original_codewords")
    decoded_codewords = _to_2d_array(decoded_codewords, "decoded_codewords")

    if original_codewords.shape != decoded_codewords.shape:
        raise ValueError("original_codewords и decoded_codewords должны иметь одинаковую форму")

    message_count = original_codewords.shape[0]

    success_flags = _to_bool_flags(
        flags=success_flags,
        length=message_count,
        default=True,
        name="success_flags",
    )

    codeword_errors = np.any(original_codewords != decoded_codewords, axis=1)
    packet_errors = np.logical_or(codeword_errors, ~success_flags)

    return float(np.mean(packet_errors))


def failure_rate(success_flags: np.ndarray) -> float:
    """
    Доля неуспешных декодирований.
    """
    success_flags = np.asarray(success_flags, dtype=bool).reshape(-1)

    if len(success_flags) == 0:
        raise ValueError("success_flags не должен быть пустым")

    return float(1.0 - np.mean(success_flags))


def ambiguous_rate(ambiguous_flags: np.ndarray) -> float:
    """
    Доля неоднозначных решений декодера.
    """
    ambiguous_flags = np.asarray(ambiguous_flags, dtype=bool).reshape(-1)

    if len(ambiguous_flags) == 0:
        raise ValueError("ambiguous_flags не должен быть пустым")

    return float(np.mean(ambiguous_flags))


def calculate_batch_metrics(
    original_messages: np.ndarray,
    decoded_messages: np.ndarray,
    success_flags: np.ndarray,
    ambiguous_flags: np.ndarray,
    total_time_sec: float,
    original_codewords: Optional[np.ndarray] = None,
    decoded_codewords: Optional[np.ndarray] = None,
) -> BatchMetrics:
    """
    Считает все основные метрики для одного декодера.

    original_messages:
        исходные информационные сообщения

    decoded_messages:
        восстановленные информационные сообщения

    success_flags:
        флаг успешности декодирования для каждого сообщения

    ambiguous_flags:
        флаг неоднозначности решения для каждого сообщения

    total_time_sec:
        полное время работы декодера на всём наборе сообщений

    original_codewords / decoded_codewords:
        нужны для оценки пакетных ошибок по кодовым словам
    """
    original_messages = _to_2d_array(original_messages, "original_messages")
    decoded_messages = _to_2d_array(decoded_messages, "decoded_messages")

    if original_messages.shape != decoded_messages.shape:
        raise ValueError("original_messages и decoded_messages должны иметь одинаковую форму")

    message_count, message_length = original_messages.shape

    success_flags = _to_bool_flags(
        flags=success_flags,
        length=message_count,
        default=True,
        name="success_flags",
    )

    ambiguous_flags = _to_bool_flags(
        flags=ambiguous_flags,
        length=message_count,
        default=False,
        name="ambiguous_flags",
    )

    if total_time_sec < 0:
        raise ValueError("total_time_sec не может быть отрицательным")

    bit_errors_by_row = np.sum(original_messages != decoded_messages, axis=1)
    bit_errors_by_row = bit_errors_by_row.astype(int)
    bit_errors_by_row[~success_flags] = message_length

    bit_errors = int(np.sum(bit_errors_by_row))
    total_bits = int(message_count * message_length)
    ber = float(bit_errors / total_bits)

    message_errors = np.any(original_messages != decoded_messages, axis=1)
    packet_errors_flags = np.logical_or(message_errors, ~success_flags)

    packet_errors = int(np.sum(packet_errors_flags))
    per = float(packet_errors / message_count)

    frame_errors = packet_errors
    fer = per

    codeword_packet_errors = None
    codeword_per = None

    if original_codewords is not None and decoded_codewords is not None:
        original_codewords = _to_2d_array(original_codewords, "original_codewords")
        decoded_codewords = _to_2d_array(decoded_codewords, "decoded_codewords")

        if original_codewords.shape != decoded_codewords.shape:
            raise ValueError(
                "original_codewords и decoded_codewords должны иметь одинаковую форму"
            )

        if original_codewords.shape[0] != message_count:
            raise ValueError(
                "Количество кодовых слов должно совпадать с количеством сообщений"
            )

        codeword_errors = np.any(original_codewords != decoded_codewords, axis=1)
        codeword_packet_errors_flags = np.logical_or(codeword_errors, ~success_flags)

        codeword_packet_errors = int(np.sum(codeword_packet_errors_flags))
        codeword_per = float(codeword_packet_errors / message_count)

    failure_count = int(np.sum(~success_flags))
    failure = float(failure_count / message_count)

    ambiguous_count = int(np.sum(ambiguous_flags))
    ambiguous = float(ambiguous_count / message_count)

    avg_time_ms = float((total_time_sec / message_count) * 1000.0)

    return BatchMetrics(
        total_messages=message_count,

        bit_errors=bit_errors,
        total_bits=total_bits,
        ber=ber,

        packet_errors=packet_errors,
        packet_error_rate=per,

        frame_errors=frame_errors,
        frame_error_rate=fer,

        codeword_packet_errors=codeword_packet_errors,
        codeword_packet_error_rate=codeword_per,

        failure_count=failure_count,
        failure_rate=failure,

        ambiguous_count=ambiguous_count,
        ambiguous_rate=ambiguous,

        total_time_sec=float(total_time_sec),
        avg_time_ms=avg_time_ms,
    )