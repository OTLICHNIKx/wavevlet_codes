from typing import Optional

import numpy as np

from wavelet_codes import WaveletCode


def is_prime(number: int) -> bool:
    """
    Проверяет, является ли число простым.
    Для GF(p) нам нужна простая характеристика поля p.
    """
    if number < 2:
        return False

    if number == 2:
        return True

    if number % 2 == 0:
        return False

    divisor = 3

    while divisor * divisor <= number:
        if number % divisor == 0:
            return False
        divisor += 2

    return True


def read_int(prompt: str, default: Optional[int] = None) -> int:
    """
    Считывает целое число.
    Если задан default, то пустой ввод заменяется значением по умолчанию.
    """
    while True:
        raw_value = input(prompt).strip()

        if raw_value == "" and default is not None:
            return default

        try:
            return int(raw_value)
        except ValueError:
            print("Ошибка: нужно ввести целое число.")


def read_prime_field() -> int:
    """
    Считывает характеристику поля GF(p).
    """
    while True:
        field = read_int("Введите характеристику поля p [2]: ", default=2)

        if is_prime(field):
            return field

        print("Ошибка: p должно быть простым числом. Например: 2, 3, 5, 7, 11.")


def read_vector(prompt: str, field: int) -> list[int]:
    """
    Считывает вектор элементов поля.

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
            print("Ошибка: вектор должен содержать только целые числа.")
            continue

        invalid_values = [value for value in vector if value < 0 or value >= field]

        if invalid_values:
            print(
                f"Ошибка: элементы должны принадлежать GF({field}), "
                f"то есть быть в диапазоне от 0 до {field - 1}."
            )
            continue

        return vector


def print_matrix(title: str, matrix: np.ndarray) -> None:
    """
    Красиво печатает матрицу.
    """
    print(f"\n{title}:")
    for row in matrix:
        print(" ".join(str(int(value)) for value in row))


def main() -> None:
    print("Построение и кодирование линейного вейвлетного кода")
    print("-" * 55)

    field = read_prime_field()

    if field != 2:
        print(
            "\nПредупреждение: сейчас кодирование работает над GF(p), "
            "но дальнейшая BPSK-модуляция обычно предполагает бинарный случай GF(2)."
        )

    h = read_vector(
        prompt=f"\nВведите коэффициенты h через пробел или запятую, элементы GF({field}): ",
        field=field,
    )

    if len(h) % 2 != 0:
        print("\nОшибка: количество коэффициентов h должно быть чётным.")
        return

    message = read_vector(
        prompt=f"Введите информационное слово v, элементы GF({field}): ",
        field=field,
    )

    codeword_length = 2 * len(message)

    if len(h) > codeword_length:
        print(
            "\nОшибка: количество коэффициентов h не может быть больше длины кодового слова."
        )
        print(f"len(h) = {len(h)}, n = {codeword_length}")
        return

    a = 1

    try:
        code = WaveletCode.from_scaling_coefficients(
            h=h,
            codeword_length=codeword_length,
            field=field,
            a=a,
            name="Interactive wavelet code",
        )
    except ValueError as error:
        print("\nОшибка при построении кода:")
        print(error)
        return

    codeword = code.encode(message)

    print("\nРезультат")
    print("-" * 55)

    print("Код:", code.name)
    print(f"Поле: GF({field})")
    print("k =", code.k)
    print("n =", code.n)
    print("a =", a)

    print("\nКоэффициенты h:")
    print(code.components["h"].tolist())

    print("\nКоэффициенты g:")
    print(code.components["g"].tolist())

    print_matrix("Матрица H_wavelet", code.components["H_wavelet"])
    print_matrix("Матрица G_wavelet", code.components["G_wavelet"])
    print_matrix("Матрица J", code.components["J"])
    print_matrix("Порождающая матрица G_C размера k x n", code.generator_matrix)

    print("\nИнформационное слово v:")
    print(message)

    print("\nКодовое слово x:")
    print(codeword.tolist())


if __name__ == "__main__":
    main()