from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np


def to_field_vector(values: Iterable[int], field: int, name: str = "vector") -> np.ndarray:
    """
    Преобразует вход в вектор над GF(field).
    Сейчас считаем, что field — простое число, например 2.
    """
    vector = np.asarray(list(values))

    if vector.ndim != 1:
        raise ValueError(f"{name} должен быть одномерным вектором")

    if not np.all(np.isclose(vector, np.round(vector))):
        raise ValueError(f"{name} должен содержать только целые числа")

    return np.mod(np.round(vector).astype(int), field)


def to_field_matrix(values: Iterable[Iterable[int]], field: int, name: str = "matrix") -> np.ndarray:
    """
    Преобразует вход в матрицу над GF(field).
    """
    matrix = np.asarray(values)

    if matrix.ndim != 2:
        raise ValueError(f"{name} должна быть двумерной матрицей")

    if not np.all(np.isclose(matrix, np.round(matrix))):
        raise ValueError(f"{name} должна содержать только целые числа")

    return np.mod(np.round(matrix).astype(int), field)


def gf_matmul(left: np.ndarray, right: np.ndarray, field: int) -> np.ndarray:
    """
    Умножение над GF(field).
    """
    return np.mod(left @ right, field)


def gf_rank(matrix: np.ndarray, field: int) -> int:
    """
    Ранг матрицы над GF(field).
    Используем для проверки, что порождающая матрица не вырождена.
    """
    a = np.mod(matrix.copy(), field)
    rows, cols = a.shape
    rank = 0

    for col in range(cols):
        pivot = None

        for row in range(rank, rows):
            if a[row, col] % field != 0:
                pivot = row
                break

        if pivot is None:
            continue

        if pivot != rank:
            a[[rank, pivot]] = a[[pivot, rank]]

        inverse = pow(int(a[rank, col]), -1, field)
        a[rank] = np.mod(a[rank] * inverse, field)

        for row in range(rows):
            if row != rank and a[row, col] % field != 0:
                factor = a[row, col]
                a[row] = np.mod(a[row] - factor * a[rank], field)

        rank += 1

    return rank


def build_detail_coefficients(h: Iterable[int], field: int) -> np.ndarray:
    """
    Строит коэффициенты вейвлетной функции g через коэффициенты h.

    Формула:
        g_n = (-1)^n * h_{L - 1 - n}

    В GF(2) знак -1 совпадает с 1, поэтому минус исчезает.
    """
    h_vector = to_field_vector(h, field, name="h")
    length = len(h_vector)

    if length % 2 != 0:
        raise ValueError("Количество коэффициентов h должно быть чётным")

    g = []

    for n in range(length):
        sign = 1 if n % 2 == 0 else -1
        value = sign * h_vector[length - 1 - n]
        g.append(value)

    return to_field_vector(g, field, name="g")


def build_cyclic_filter_matrix(
    coefficients: Iterable[int],
    codeword_length: int,
    field: int,
    step: int = 2,
) -> np.ndarray:
    """
    Строитциклическую  матрицу фильтра.

    Для кода длины n матрица имеет размер:
        k x n, где k = n / 2

    Каждая следующая строка — циклический сдвиг фильтра.
    """
    coeffs = to_field_vector(coefficients, field, name="coefficients")
    n = codeword_length

    if n % 2 != 0:
        raise ValueError("Длина кодового слова должна быть чётной")

    if len(coeffs) > n:
        raise ValueError("Количество коэффициентов не может быть больше длины кодового слова")

    k = n // 2
    matrix = np.zeros((k, n), dtype=int)

    for row in range(k):
        start = (step * row) % n

        for offset, coeff in enumerate(coeffs):
            col = (start + offset) % n
            matrix[row, col] = (matrix[row, col] + coeff) % field

    return matrix


def build_shift_matrix(size: int, field: int, shift: int = 1) -> np.ndarray:
    """
    Строит циклическую матрицу сдвига J размера size x size.
    """
    matrix = np.zeros((size, size), dtype=int)

    for row in range(size):
        col = (row + shift) % size
        matrix[row, col] = 1

    return np.mod(matrix, field)


def build_wavelet_generator_matrix(
    h: Iterable[int],
    codeword_length: int,
    field: int = 2,
    a: int = 1,
    shift: int = 1,
    check_rank: bool = True,
) -> tuple[np.ndarray, dict]:
    """
    Строит порождающую матрицу линейного вейвлетного кода.

    Теоретическая формула:
        G_C = H^T + a * G^T * J

    В программе возвращаем матрицу размера k x n,
    чтобы кодировать строкой:
        codeword = message @ generator_matrix
    """
    h_vector = to_field_vector(h, field, name="h")
    g_vector = build_detail_coefficients(h_vector, field)

    n = codeword_length
    k = n // 2

    h_matrix = build_cyclic_filter_matrix(
        coefficients=h_vector,
        codeword_length=n,
        field=field,
    )

    g_matrix = build_cyclic_filter_matrix(
        coefficients=g_vector,
        codeword_length=n,
        field=field,
    )

    j_matrix = build_shift_matrix(
        size=k,
        field=field,
        shift=shift,
    )

    # Математическая матрица G_C имеет размер n x k.
    generator_column_form = np.mod(
        h_matrix.T + (a % field) * gf_matmul(g_matrix.T, j_matrix, field),
        field,
    )

    # Для Python удобнее k x n.
    generator_matrix = generator_column_form.T

    if check_rank:
        rank = gf_rank(generator_matrix, field)

        if rank < k:
            raise ValueError(
                f"Порождающая матрица вырождена: rank = {rank}, а должен быть k = {k}. "
                f"Нужно выбрать другие коэффициенты h или параметр a."
            )

    components = {
        "h": h_vector,
        "g": g_vector,
        "H_wavelet": h_matrix,
        "G_wavelet": g_matrix,
        "J": j_matrix,
        "G_C_column_form": generator_column_form,
        "generator_matrix": generator_matrix,
    }

    return generator_matrix, components


@dataclass
class WaveletCode:
    """
    Линейный вейвлетный код, заданный порождающей матрицей.

    Используем соглашение:
        generator_matrix имеет размер k x n
        message имеет длину k
        codeword = message @ generator_matrix mod field
    """

    generator_matrix: np.ndarray
    field: int = 2
    name: str = "Wavelet code"
    components: Optional[dict] = None

    def __post_init__(self) -> None:
        self.generator_matrix = to_field_matrix(
            self.generator_matrix,
            field=self.field,
            name="generator_matrix",
        )

        rank = gf_rank(self.generator_matrix, self.field)

        if rank < self.k:
            raise ValueError(
                f"Порождающая матрица должна иметь ранг k = {self.k}, "
                f"получен rank = {rank}"
            )

    @property
    def k(self) -> int:
        return self.generator_matrix.shape[0]

    @property
    def n(self) -> int:
        return self.generator_matrix.shape[1]

    @classmethod
    def from_scaling_coefficients(
        cls,
        h: Iterable[int],
        codeword_length: int,
        field: int = 2,
        a: int = 1,
        shift: int = 1,
        name: str = "Wavelet code from scaling coefficients",
    ) -> "WaveletCode":
        generator_matrix, components = build_wavelet_generator_matrix(
            h=h,
            codeword_length=codeword_length,
            field=field,
            a=a,
            shift=shift,
        )

        return cls(
            generator_matrix=generator_matrix,
            field=field,
            name=name,
            components=components,
        )

    def encode(self, message: Iterable[int]) -> np.ndarray:
        message_vector = to_field_vector(
            message,
            field=self.field,
            name="message",
        )

        if len(message_vector) != self.k:
            raise ValueError(
                f"Длина сообщения должна быть k = {self.k}, "
                f"получено {len(message_vector)}"
            )

        return gf_matmul(message_vector, self.generator_matrix, self.field)