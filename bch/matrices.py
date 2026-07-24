from dataclasses import dataclass

import numpy as np

from .generator import BCHGeneratorResult

from .polynomial import (
    gf2_polynomial_degree,
    gf2_polynomial_divmod,
    gf2_polynomial_reciprocal,
)


def to_binary_matrix(
    values: object,
    name: str = "matrix",
) -> np.ndarray:
    """
    Преобразует вход в бинарную матрицу numpy.

    Функция не исправляет значения по модулю 2 автоматически:
    вход должен уже содержать только 0 и 1.
    """
    matrix = np.asarray(values)

    if matrix.ndim != 2:
        raise ValueError(
            f"{name} должна быть двумерной матрицей"
        )

    if not np.all(
        (matrix == 0) | (matrix == 1)
    ):
        raise ValueError(
            f"{name} должна содержать только 0 и 1"
        )

    return matrix.astype(np.uint8)


def gf2_row_reduce(
    matrix: object,
) -> tuple[np.ndarray, tuple[int, ...]]:
    """
    Приводит бинарную матрицу к приведённому ступенчатому виду
    над GF(2).

    Возвращает:

        reduced_matrix
        pivot_columns
    """
    reduced = to_binary_matrix(
        matrix,
        name="matrix",
    ).copy()

    row_count, column_count = reduced.shape

    pivot_columns: list[int] = []
    pivot_row = 0

    for column in range(column_count):
        if pivot_row >= row_count:
            break

        candidates = np.flatnonzero(
            reduced[pivot_row:, column]
        )

        if candidates.size == 0:
            continue

        selected_row = (
            pivot_row + int(candidates[0])
        )

        if selected_row != pivot_row:
            reduced[
                [pivot_row, selected_row]
            ] = reduced[
                [selected_row, pivot_row]
            ]

        for row in range(row_count):
            if row == pivot_row:
                continue

            if reduced[row, column] == 1:
                reduced[row] ^= reduced[pivot_row]

        pivot_columns.append(column)
        pivot_row += 1

    return reduced, tuple(pivot_columns)


def gf2_matrix_rank(
    matrix: object,
) -> int:
    """
    Вычисляет ранг бинарной матрицы над GF(2).
    """
    _, pivot_columns = gf2_row_reduce(matrix)

    return len(pivot_columns)


def integer_polynomial_to_vector(
    polynomial: int,
    length: int,
) -> np.ndarray:
    """
    Преобразует двоичный полином в вектор коэффициентов.

    Коэффициенты располагаются от младшей степени
    к старшей:

        [p_0, p_1, ..., p_(length-1)]
    """
    if not isinstance(polynomial, int):
        raise TypeError(
            "polynomial должен быть целым числом"
        )

    if polynomial < 0:
        raise ValueError(
            "polynomial не может быть отрицательным"
        )

    if not isinstance(length, int):
        raise TypeError(
            "length должен быть целым числом"
        )

    if length <= 0:
        raise ValueError(
            "length должен быть положительным"
        )

    if gf2_polynomial_degree(polynomial) >= length:
        raise ValueError(
            "Степень полинома не помещается "
            f"в вектор длины {length}"
        )

    return np.asarray(
        [
            (polynomial >> degree) & 1
            for degree in range(length)
        ],
        dtype=np.uint8,
    )


def build_shifted_polynomial_matrix(
    polynomial: int,
    codeword_length: int,
    row_count: int,
) -> np.ndarray:
    """
    Строит циклическую матрицу из последовательных
    сдвигов полинома:

        polynomial
        x * polynomial
        x^2 * polynomial
        ...

    В матрицу входят row_count строк.
    """
    if not isinstance(polynomial, int):
        raise TypeError(
            "polynomial должен быть целым числом"
        )

    if polynomial <= 0:
        raise ValueError(
            "polynomial должен быть ненулевым"
        )

    if not isinstance(codeword_length, int):
        raise TypeError(
            "codeword_length должен быть целым числом"
        )

    if codeword_length <= 0:
        raise ValueError(
            "codeword_length должен быть положительным"
        )

    if not isinstance(row_count, int):
        raise TypeError(
            "row_count должен быть целым числом"
        )

    if row_count <= 0:
        raise ValueError(
            "row_count должен быть положительным"
        )

    polynomial_degree = gf2_polynomial_degree(
        polynomial
    )

    if polynomial_degree + row_count > codeword_length:
        raise ValueError(
            "Сдвиги полинома не помещаются в кодовое слово: "
            f"degree = {polynomial_degree}, "
            f"row_count = {row_count}, "
            f"n = {codeword_length}"
        )

    rows = []

    for shift in range(row_count):
        shifted_polynomial = polynomial << shift

        row = integer_polynomial_to_vector(
            polynomial=shifted_polynomial,
            length=codeword_length,
        )

        rows.append(row)

    return np.vstack(rows).astype(np.uint8)


def build_bch_generator_matrix(
    construction: BCHGeneratorResult,
) -> np.ndarray:
    """
    Строит порождающую матрицу G BCH-кода.

    Каждая строка соответствует полиному:

        x^i * g(x)

    где:

        i = 0, 1, ..., k - 1
    """
    expected_degree = construction.n - construction.k

    actual_degree = gf2_polynomial_degree(
        construction.generator_polynomial
    )

    if actual_degree != expected_degree:
        raise ValueError(
            "Степень порождающего полинома "
            "не соответствует параметрам кода: "
            f"degree = {actual_degree}, "
            f"n - k = {expected_degree}"
        )

    generator_matrix = build_shifted_polynomial_matrix(
        polynomial=construction.generator_polynomial,
        codeword_length=construction.n,
        row_count=construction.k,
    )

    rank = gf2_matrix_rank(generator_matrix)

    if rank != construction.k:
        raise ValueError(
            "Порождающая матрица BCH имеет неверный ранг: "
            f"rank = {rank}, k = {construction.k}"
        )

    return generator_matrix


def build_bch_parity_check_matrix(
    construction: BCHGeneratorResult,
) -> tuple[np.ndarray, int, int]:
    """
    Строит проверочную матрицу H BCH-кода.

    Сначала находим проверочный полином:

        h(x) = (x^n + 1) / g(x)

    В GF(2):

        x^n - 1 = x^n + 1

    Затем строим порождающий полином двойственного кода:

        g_dual(x) = reciprocal(h(x))

    Строки проверочной матрицы H являются
    последовательными сдвигами g_dual(x).

    Возвращает:

        parity_check_matrix
        check_polynomial
        dual_generator_polynomial
    """
    x_n_plus_one = (
        1 << construction.n
    ) | 1

    check_polynomial, remainder = (
        gf2_polynomial_divmod(
            dividend=x_n_plus_one,
            divisor=construction.generator_polynomial,
        )
    )

    if remainder != 0:
        raise ValueError(
            "Порождающий полином не делит x^n + 1"
        )

    dual_generator_polynomial = (
        gf2_polynomial_reciprocal(
            check_polynomial
        )
    )

    parity_check_row_count = (
        construction.n - construction.k
    )

    parity_check_matrix = (
        build_shifted_polynomial_matrix(
            polynomial=dual_generator_polynomial,
            codeword_length=construction.n,
            row_count=parity_check_row_count,
        )
    )

    rank = gf2_matrix_rank(
        parity_check_matrix
    )

    if rank != parity_check_row_count:
        raise ValueError(
            "Проверочная матрица BCH имеет неверный ранг: "
            f"rank = {rank}, "
            f"ожидалось {parity_check_row_count}"
        )

    return (
        parity_check_matrix,
        check_polynomial,
        dual_generator_polynomial,
    )


def validate_bch_matrices(
    generator_matrix: object,
    parity_check_matrix: object,
) -> None:
    """
    Проверяет согласованность порождающей и проверочной матриц.

    Необходимые условия:

        G имеет размер k x n;
        H имеет размер (n-k) x n;
        rank(G) = k;
        rank(H) = n-k;
        G @ H.T = 0 mod 2.
    """
    generator = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    parity_check = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    k, n = generator.shape
    parity_rows, parity_n = parity_check.shape

    if parity_n != n:
        raise ValueError(
            "Матрицы G и H должны иметь "
            "одинаковое количество столбцов"
        )

    if k + parity_rows != n:
        raise ValueError(
            "Размеры матриц не соответствуют "
            "линейному коду: "
            f"k = {k}, rows(H) = {parity_rows}, n = {n}"
        )

    generator_rank = gf2_matrix_rank(generator)

    if generator_rank != k:
        raise ValueError(
            "Матрица G не имеет полного строкового ранга: "
            f"rank = {generator_rank}, k = {k}"
        )

    parity_rank = gf2_matrix_rank(parity_check)

    if parity_rank != parity_rows:
        raise ValueError(
            "Матрица H не имеет полного строкового ранга: "
            f"rank = {parity_rank}, "
            f"rows = {parity_rows}"
        )

    product = np.mod(
        generator.astype(np.int64)
        @ parity_check.astype(np.int64).T,
        2,
    )

    if not np.all(product == 0):
        raise ValueError(
            "Матрицы G и H не согласованы: "
            "G @ H.T должно быть равно нулю"
        )


@dataclass
class BCHMatrices:
    """
    Матрицы и полиномы, описывающие BCH-код.
    """

    generator_matrix: np.ndarray
    parity_check_matrix: np.ndarray

    check_polynomial: int
    dual_generator_polynomial: int

    def __post_init__(self) -> None:
        self.generator_matrix = to_binary_matrix(
            self.generator_matrix,
            name="generator_matrix",
        )

        self.parity_check_matrix = to_binary_matrix(
            self.parity_check_matrix,
            name="parity_check_matrix",
        )

        validate_bch_matrices(
            generator_matrix=self.generator_matrix,
            parity_check_matrix=self.parity_check_matrix,
        )


def build_bch_matrices(
    construction: BCHGeneratorResult,
) -> BCHMatrices:
    """
    Строит полный комплект матриц BCH-кода.
    """
    generator_matrix = (
        build_bch_generator_matrix(construction)
    )

    (
        parity_check_matrix,
        check_polynomial,
        dual_generator_polynomial,
    ) = build_bch_parity_check_matrix(
        construction
    )

    matrices = BCHMatrices(
        generator_matrix=generator_matrix,
        parity_check_matrix=parity_check_matrix,
        check_polynomial=check_polynomial,
        dual_generator_polynomial=(
            dual_generator_polynomial
        ),
    )

    if matrices.generator_matrix.shape != (
        construction.k,
        construction.n,
    ):
        raise ValueError(
            "Получен неверный размер матрицы G"
        )

    if matrices.parity_check_matrix.shape != (
        construction.n - construction.k,
        construction.n,
    ):
        raise ValueError(
            "Получен неверный размер матрицы H"
        )

    return matrices