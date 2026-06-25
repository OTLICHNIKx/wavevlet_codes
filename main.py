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

from decode.syndrome_decoding import syndrome_decode
from decode.maximum_likelihood_decoding import (
    hard_maximum_likelihood_decode,
    soft_maximum_likelihood_decode,
)
from decode.chase_decoding import chase_decode

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

    chase_unreliable_positions_count = read_optional_int(
        "Введите число наименее надёжных позиций для алгоритма Чейза p [2]: ",
        default=2,
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

        parity_check_matrix = code.components["parity_check_matrix"]

        syndrome_result = syndrome_decode(
            received_word=hard_bits,
            parity_check_matrix=parity_check_matrix,
            generator_matrix=code.generator_matrix,
            max_error_weight=1,
        )

        hard_mld_result = hard_maximum_likelihood_decode(
            received_word=hard_bits,
            generator_matrix=code.generator_matrix,
        )

        soft_mld_result = soft_maximum_likelihood_decode(
            received_symbols=received_symbols,
            generator_matrix=code.generator_matrix,
        )

        chase_result = chase_decode(
            received_word=hard_bits,
            received_symbols=received_symbols,
            reliability=reliability,
            parity_check_matrix=parity_check_matrix,
            generator_matrix=code.generator_matrix,
            unreliable_positions_count=chase_unreliable_positions_count,
            inner_decoder_max_error_weight=1,
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

    print_matrix("Матрица H_direct", code.components["H_direct"])
    print_matrix("Матрица G_direct", code.components["G_direct"])
    print_matrix("Матрица H_inverse", code.components["H_inverse"])
    print_matrix("Матрица G_inverse", code.components["G_inverse"])
    print_matrix("Проверочная матрица H_C", code.components["parity_check_matrix"])
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
        "Проверочная матрица H_C по вейвлетной формуле",
        parity_check_matrix,
    )

    print("Синдром:", syndrome_result.syndrome.tolist())

    if syndrome_result.success:
        print("Найденный вектор ошибки:", syndrome_result.error_vector.tolist())
        print("Исправленное кодовое слово:", syndrome_result.corrected_word.tolist())
        print("Статус:", syndrome_result.message)
    else:
        print("Вектор ошибки не найден.")
        print("Слово оставлено без исправления:", syndrome_result.corrected_word.tolist())

    print("\nЭтап 6. Декодирование методом максимального правдоподобия")

    print("\nHard MLD")
    print("Метрика:", hard_mld_result.metric_name)
    print("Перебрано кодовых слов:", hard_mld_result.candidates_count)
    print("Минимальная метрика:", hard_mld_result.metric)
    print("Неоднозначность:", "да" if hard_mld_result.ambiguous else "нет")
    print("Лучшее кодовое слово:", hard_mld_result.decoded_codeword.tolist())
    print("Восстановленное информационное слово:", hard_mld_result.decoded_message.tolist())
    print("Статус:", hard_mld_result.message)

    print("\nSoft MLD")
    print("Метрика:", soft_mld_result.metric_name)
    print("Перебрано кодовых слов:", soft_mld_result.candidates_count)
    print("Минимальная метрика:", round(soft_mld_result.metric, 6))
    print("Неоднозначность:", "да" if soft_mld_result.ambiguous else "нет")
    print("Лучшее кодовое слово:", soft_mld_result.decoded_codeword.tolist())
    print("Восстановленное информационное слово:", soft_mld_result.decoded_message.tolist())
    print("Статус:", soft_mld_result.message)

    print("\nЭтап 7. Декодирование алгоритмом Чейза")

    print("Количество наименее надёжных позиций p:", chase_unreliable_positions_count)
    print("Наименее надёжные позиции:", chase_result.unreliable_positions.tolist())
    print("Количество успешных кандидатов:", chase_result.candidates_count)

    if not chase_result.success:
        print("Статус:", chase_result.message)
    else:
        print("Минимальная евклидова метрика:", round(chase_result.metric, 6))
        print("Неоднозначность:", "да" if chase_result.ambiguous else "нет")
        print("Лучшее кодовое слово:", chase_result.decoded_codeword.tolist())

        if chase_result.decoded_message is not None:
            print(
                "Восстановленное информационное слово:",
                chase_result.decoded_message.tolist(),
            )

        print("Статус:", chase_result.message)

        print("\nКандидаты Чейза:")
        for index, candidate in enumerate(chase_result.candidates, start=1):
            print(f"  Кандидат {index}:")
            print("    test_pattern:", candidate.test_pattern.tolist())
            print("    trial_word:", candidate.trial_word.tolist())
            print("    decoded_codeword:", candidate.decoded_codeword.tolist())
            print("    metric:", round(candidate.metric, 6))

            if candidate.decoded_message is not None:
                print("    decoded_message:", candidate.decoded_message.tolist())

if __name__ == "__main__":
    main()