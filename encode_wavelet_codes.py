from wavelet_codes import WaveletCode


def main() -> None:
    # Демонстрационная порождающая матрица.
    # Размер: k x n = 4 x 8.
    #
    # В реальном проекте сюда нужно поставить порождающую матрицу
    # именно твоего линейного вейвлетного кода.
    G = [
        [1, 0, 0, 0, 1, 1, 0, 1],
        [0, 1, 0, 0, 1, 0, 1, 1],
        [0, 0, 1, 0, 0, 1, 1, 1],
        [0, 0, 0, 1, 1, 1, 1, 0],
    ]

    code = WaveletCode(
        generator_matrix=G,
        name="Demo binary wavelet code"
    )

    message = [1, 0, 1, 1]

    codeword = code.encode(message)

    print("Код:", code.name)
    print("k =", code.k)
    print("n =", code.n)
    print("Информационное сообщение:", message)
    print("Кодовое слово:", codeword.tolist())


if __name__ == "__main__":
    main()