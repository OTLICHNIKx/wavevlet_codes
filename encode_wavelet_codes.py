import numpy as np

from wavelet_codes import WaveletCode


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
            print("Ошибка: вектор должен содержать только числа 0 и 1.")
            continue

        invalid_values = [value for value in vector if value not in (0, 1)]

        if invalid_values:
            print("Ошибка: в бинарном коде элементы должны быть только 0 или 1.")
            continue

        return vector


def print_matrix(title: str, matrix: np.ndarray) -> None:
    """
    Печатает матрицу в удобном виде.
    """
    print(f"\n{title}:")
    for row in matrix:
        print(" ".join(str(int(value)) for value in row))


def main() -> None:
    print("Кодирование линейного вейвлетного кода над GF(2)")
    print("-" * 60)

    field = 2

    h = read_binary_vector(
        "Введите коэффициенты масштабирующей функции h: "
    )

    if len(h) % 2 != 0:
        print("\nОшибка: количество коэффициентов h должно быть чётным.")
        return

    message = read_binary_vector(
        "Введите информационное слово v: "
    )

    codeword_length = 2 * len(message)

    if len(h) > codeword_length:
        print("\nОшибка: количество коэффициентов h не может быть больше длины кодового слова.")
        print(f"len(h) = {len(h)}, n = {codeword_length}")
        return

    a = 1

    try:
        code = WaveletCode.from_scaling_coefficients(
            h=h,
            codeword_length=codeword_length,
            field=field,
            a=a,
            name="Binary wavelet code",
        )
    except ValueError as error:
        print("\nОшибка при построении кода:")
        print(error)
        return

    codeword = code.encode(message)

    print("\nРезультат")
    print("-" * 60)

    print("Код:", code.name)
    print("Поле: GF(2)")
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