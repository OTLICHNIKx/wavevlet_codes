from wavelet_codes import WaveletCode


def main() -> None:
    # Работаем над GF(2), то есть все операции выполняются по модулю 2.
    field = 2

    # Коэффициенты масштабирующей функции h.
    #
    # Пока берём простой учебный набор коэффициентов над GF(2).
    # Позже сюда можно будет подставить коэффициенты из конкретного варианта.
    h = [1, 0]

    # Длина кодового слова n.
    # Для вейвлетного кода первого порядка k = n / 2.
    codeword_length = 8

    # Параметр a из формулы:
    # G_C = H^T + a * G^T * J
    #
    # Для GF(2) обычно берём a = 1.
    a = 1

    code = WaveletCode.from_scaling_coefficients(
        h=h,
        codeword_length=codeword_length,
        field=field,
        a=a,
        name="Demo binary wavelet code",
    )

    message = [1, 0, 1, 1]

    codeword = code.encode(message)

    print("Код:", code.name)
    print("Поле: GF(2)")
    print("k =", code.k)
    print("n =", code.n)

    print("\nКоэффициенты h:")
    print(code.components["h"].tolist())

    print("\nКоэффициенты g:")
    print(code.components["g"].tolist())

    print("\nМатрица H_wavelet:")
    print(code.components["H_wavelet"])

    print("\nМатрица G_wavelet:")
    print(code.components["G_wavelet"])

    print("\nМатрица J:")
    print(code.components["J"])

    print("\nПорождающая матрица generator_matrix размера k x n:")
    print(code.generator_matrix)

    print("\nИнформационное сообщение:")
    print(message)

    print("\nКодовое слово:")
    print(codeword.tolist())


if __name__ == "__main__":
    main()