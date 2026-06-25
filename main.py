from typing import Optional

import numpy as np

from channel.awgn import awgn_channel
from encode_wavelet_codes import encode_wavelet_message
from modulation.modulator import bpsk_modulate
from modulation.demodulator import (
    bpsk_llr,
    hard_decision_from_llr,
    reliability_from_llr,
)

from decode.syndrome_decoding import (
    build_parity_check_matrix_from_generator,
    syndrome_decode,
)


def read_binary_vector(prompt: str) -> list[int]:
    """
    Считывает бинарный вектор.

    Можно вводить:
        1 0 1 1
    или:
        1,0,1,1
    """
    while True:
        raw_value = input(prompt).strip()

        if not raw_value:
            print("Ошибка: вектор не должен быть пустым.")
            continue

        raw_value = raw_value.replace(",", " ")
        parts = raw_value.split()

        try:
            vector = [int(part) for part in parts]
        except ValueError:
            print("Ошибка: нужно ввести только числа 0 и 1.")
            continue

        if any(value not in (0, 1) for value in vector):
            print("Ошибка: элементы должны быть только 0 или 1.")
            continue

        return vector


def read_positive_float(prompt: str, default: float) -> float:
    """
    Считывает положительное вещественное число.
    """
    while True:
        raw_value = input(prompt).strip()

        if raw_value == "":
            return default

        try:
            value = float(raw_value)
        except ValueError:
            print("Ошибка: нужно ввести число.")
            continue

        if value <= 0:
            print("Ошибка: значение должно быть положительным.")
            continue

        return value


def read_optional_int(prompt: str, default: Optional[int] = None) -> Optional[int]:
    """
    Считывает целое число или возвращает default при пустом вводе.
    """
    while True:
        raw_value = input(prompt).strip()

        if raw_value == "":
            return default

        try:
            return int(raw_value)
        except ValueError:
            print("Ошибка: нужно ввести целое число.")


def print_matrix(title: str, matrix: np.ndarray) -> None:
    print(f"\n{title}:")
    for row in matrix:
        print(" ".join(str(int(value)) for value in row))


def print_float_vector(title: str, vector: np.ndarray, precision: int = 4) -> None:
    formatted = np.array2string(
        np.asarray(vector, dtype=float),
        precision=precision,
        suppress_small=True,
    )
    print(f"{title}: {formatted}")


def main() -> None:
    print("Полный цикл: кодирование -> BPSK -> канал -> LLR")
    print("-" * 70)

    h = read_binary_vector("Введите коэффициенты масштабирующей функции h: ")
    message = read_binary_vector("Введите информационное слово v: ")

    noise_std = read_positive_float(
        "Введите sigma шума для AWGN-канала [0.5]: ",
        default=0.5,
    )

    seed = read_optional_int(
        "Введите seed для генератора шума [42]: ",
        default=42,
    )

    try:
        code, codeword = encode_wavelet_message(
            h=h,
            message=message,
        )

        bpsk_symbols = bpsk_modulate(codeword)
        received_symbols = awgn_channel(
            symbols=bpsk_symbols,
            noise_std=noise_std,
            seed=seed,
        )

        llr = bpsk_llr(
            received_symbols=received_symbols,
            noise_std=noise_std,
        )

        hard_bits = hard_decision_from_llr(llr)
        reliability = reliability_from_llr(llr)

        parity_check_matrix = build_parity_check_matrix_from_generator(
            code.generator_matrix
        )

        syndrome_result = syndrome_decode(
            received_word=hard_bits,
            parity_check_matrix=parity_check_matrix,
            generator_matrix=code.generator_matrix,
            max_error_weight=1,
        )

    except ValueError as error:
        print("\nОшибка:")
        print(error)
        return

    print("\nРезультат")
    print("-" * 70)

    print("Поле: GF(2)")
    print("k =", code.k)
    print("n =", code.n)
    print("sigma шума =", noise_std)
    print("seed =", seed)

    print("\nКоэффициенты h:")
    print(code.components["h"].tolist())

    print("\nКоэффициенты g:")
    print(code.components["g"].tolist())

    print_matrix("Матрица H_wavelet", code.components["H_wavelet"])
    print_matrix("Матрица G_wavelet", code.components["G_wavelet"])
    print_matrix("Матрица J", code.components["J"])
    print_matrix("Порождающая матрица G_C размера k x n", code.generator_matrix)

    print("\nЭтап 1. Кодирование")
    print("Информационное слово v:", message)
    print("Кодовое слово x:", codeword.tolist())

    print("\nЭтап 2. BPSK-модуляция")
    print("Правило: 0 -> +1, 1 -> -1")
    print_float_vector("BPSK-символы", bpsk_symbols)

    print("\nЭтап 3. Канал AWGN")
    print_float_vector("Принятые значения после шума", received_symbols)

    print("\nЭтап 4. Демодуляция через LLR")
    print_float_vector("LLR", llr)
    print("Жёсткое решение после демодуляции:", hard_bits.tolist())
    print_float_vector("Достоверности |LLR|", reliability)

    print("\nДальше эти данные пойдут в декодер:")
    print("Принятое слово y:", hard_bits.tolist())
    print_float_vector("Достоверности l", reliability)

    print("\nЭтап 5. Синдромное декодирование")

    print_matrix(
        "Проверочная матрица H, построенная по G_C",
        parity_check_matrix,
    )

    print("Синдром:", syndrome_result.syndrome.tolist())
    print("Найденный вектор ошибки:", syndrome_result.error_vector.tolist())
    print("Исправленное кодовое слово:", syndrome_result.corrected_word.tolist())
    print("Статус:", syndrome_result.message)

    if syndrome_result.decoded_message is not None:
        print("Восстановленное информационное слово:", syndrome_result.decoded_message.tolist())


if __name__ == "__main__":
    main()