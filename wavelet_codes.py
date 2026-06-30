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

def gf_inverse_matrix(matrix: np.ndarray, field: int) -> np.ndarray:
    """
    Находит обратную матрицу над GF(field).

    Сейчас основной случай — GF(2), но функция работает и для простого field.
    """
    matrix = to_field_matrix(matrix, field=field, name="matrix")

    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Обратная матрица существует только для квадратной матрицы")

    size = matrix.shape[0]

    left = matrix.copy()
    right = np.eye(size, dtype=int)

    augmented = np.concatenate([left, right], axis=1)
    augmented = np.mod(augmented, field)

    pivot_row = 0

    for column in range(size):
        pivot = None

        for row in range(pivot_row, size):
            if augmented[row, column] % field != 0:
                pivot = row
                break

        if pivot is None:
            raise ValueError(
                "Матрица прямого вейвлетного преобразования необратима. "
                "Для выбранных коэффициентов h нельзя построить корректные "
                "матрицы обратного преобразования."
            )

        if pivot != pivot_row:
            augmented[[pivot_row, pivot]] = augmented[[pivot, pivot_row]]

        inverse = pow(int(augmented[pivot_row, column]), -1, field)
        augmented[pivot_row] = np.mod(augmented[pivot_row] * inverse, field)

        for row in range(size):
            if row != pivot_row and augmented[row, column] % field != 0:
                factor = augmented[row, column]
                augmented[row] = np.mod(
                    augmented[row] - factor * augmented[pivot_row],
                    field,
                )

        pivot_row += 1

    return np.mod(augmented[:, size:], field).astype(np.uint8)


def build_inverse_wavelet_matrices(
    h_matrix: np.ndarray,
    g_matrix: np.ndarray,
    field: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Строит матрицы обратного вейвлетного преобразования.

    Прямое преобразование:
        a = H · s
        d = G · s

    Объединённая матрица:
        A = [H]
            [G]

    Если A обратима, то:
        s = A^(-1) · [a]
                    [d]

    Из A^(-1) получаем:
        H_inverse
        G_inverse
    """
    h_matrix = to_field_matrix(h_matrix, field=field, name="H_direct")
    g_matrix = to_field_matrix(g_matrix, field=field, name="G_direct")

    if h_matrix.shape != g_matrix.shape:
        raise ValueError("Матрицы H_direct и G_direct должны иметь одинаковый размер")

    k, n = h_matrix.shape

    if 2 * k != n:
        raise ValueError(
            "Для текущей реализации ожидается код первого порядка: n = 2k"
        )

    analysis_matrix = np.vstack([h_matrix, g_matrix])
    inverse_analysis_matrix = gf_inverse_matrix(analysis_matrix, field)

    h_inverse_transposed = inverse_analysis_matrix[:, :k]
    g_inverse_transposed = inverse_analysis_matrix[:, k:]

    h_inverse_matrix = h_inverse_transposed.T
    g_inverse_matrix = g_inverse_transposed.T

    return (
        np.mod(h_inverse_matrix, field).astype(np.uint8),
        np.mod(g_inverse_matrix, field).astype(np.uint8),
    )


def check_wavelet_inverse_conditions(
    h_direct: np.ndarray,
    g_direct: np.ndarray,
    h_inverse: np.ndarray,
    g_inverse: np.ndarray,
    field: int,
) -> None:
    """
    Проверяет условия согласованности прямого и обратного преобразования.

    Проверяем:
        H_bar · H^T = I
        G_bar · G^T = I
        H_bar · G^T = 0
        G_bar · H^T = 0
        H^T · H_bar + G^T · G_bar = I
    """
    h_direct = to_field_matrix(h_direct, field=field, name="H_direct")
    g_direct = to_field_matrix(g_direct, field=field, name="G_direct")
    h_inverse = to_field_matrix(h_inverse, field=field, name="H_inverse")
    g_inverse = to_field_matrix(g_inverse, field=field, name="G_inverse")

    k, n = h_direct.shape

    identity_k = np.eye(k, dtype=int)
    identity_n = np.eye(n, dtype=int)
    zero_k = np.zeros((k, k), dtype=int)

    checks = {
        "H_inverse @ H_direct.T": (
            gf_matmul(h_inverse, h_direct.T, field),
            identity_k,
        ),
        "G_inverse @ G_direct.T": (
            gf_matmul(g_inverse, g_direct.T, field),
            identity_k,
        ),
        "H_inverse @ G_direct.T": (
            gf_matmul(h_inverse, g_direct.T, field),
            zero_k,
        ),
        "G_inverse @ H_direct.T": (
            gf_matmul(g_inverse, h_direct.T, field),
            zero_k,
        ),
        "H_direct.T @ H_inverse + G_direct.T @ G_inverse": (
            np.mod(
                gf_matmul(h_direct.T, h_inverse, field)
                + gf_matmul(g_direct.T, g_inverse, field),
                field,
            ),
            identity_n,
        ),
    }

    for name, (actual, expected) in checks.items():
        if not np.all(np.mod(actual, field) == np.mod(expected, field)):
            raise ValueError(
                f"Условие обратного вейвлетного преобразования не выполнено: {name}"
            )


def build_wavelet_parity_check_matrix(
    h_inverse: np.ndarray,
    g_inverse: np.ndarray,
    j_matrix: np.ndarray,
    field: int,
    b: int = 1,
    generator_matrix: np.ndarray | None = None,
) -> np.ndarray:
    """
    Строит проверочную матрицу H_C по обратному вейвлетному преобразованию.

    Теоретическая формула:
        H_C = H_bar^T + b · J^T · G_bar^T

    В нашей программной ориентации матрица H_C хранится как k x n,
    поэтому используем эквивалентную форму:
        H_C = H_bar + b · J^T · G_bar
    """
    h_inverse = to_field_matrix(h_inverse, field=field, name="H_inverse")
    g_inverse = to_field_matrix(g_inverse, field=field, name="G_inverse")
    j_matrix = to_field_matrix(j_matrix, field=field, name="J")

    if h_inverse.shape != g_inverse.shape:
        raise ValueError("Матрицы H_inverse и G_inverse должны иметь одинаковый размер")

    k, _ = h_inverse.shape

    if j_matrix.shape != (k, k):
        raise ValueError("Матрица J должна иметь размер k x k")

    parity_check_matrix = np.mod(
        h_inverse + (b % field) * gf_matmul(j_matrix.T, g_inverse, field),
        field,
    )

    if gf_rank(parity_check_matrix, field) < k:
        raise ValueError("Проверочная матрица H_C вырождена")

    if generator_matrix is not None:
        generator_matrix = to_field_matrix(
            generator_matrix,
            field=field,
            name="generator_matrix",
        )

        product = gf_matmul(parity_check_matrix, generator_matrix.T, field)

        if not np.all(product == 0):
            raise ValueError(
                "Проверочная матрица H_C несогласована с G_C: "
                "H_C @ G_C.T должно быть равно 0"
            )

    return parity_check_matrix.astype(np.uint8)


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
    b: int = 1,
    shift: int = 1,
    check_rank: bool = True,
    g: Optional[Iterable[int]] = None,
) -> tuple[np.ndarray, dict]:
    """
    Строит порождающую и проверочную матрицы линейного вейвлетного кода.

    Прямые матрицы:
        H_direct
        G_direct

    Обратные матрицы:
        H_inverse
        G_inverse

    Порождающая матрица:
        G_C = H^T + a * G^T * J

    Проверочная матрица:
        H_C = H_bar^T + b * J^T * G_bar^T
    """
    h_vector = to_field_vector(h, field, name="h")
    if g is None:
        g_vector = build_detail_coefficients(h_vector, field)
    else:
        g_vector = to_field_vector(g, field, name="g")

    n = codeword_length
    k = n // 2

    if len(h_vector) > n:
        raise ValueError(
            f"Количество коэффициентов h не может быть больше n: "
            f"len(h) = {len(h_vector)}, n = {n}"
        )

    if len(g_vector) > n:
        raise ValueError(
            f"Количество коэффициентов g не может быть больше n: "
            f"len(g) = {len(g_vector)}, n = {n}"
        )

    if len(h_vector) != len(g_vector):
        raise ValueError(
            f"Фильтры h и g должны иметь одинаковую длину: "
            f"len(h) = {len(h_vector)}, len(g) = {len(g_vector)}"
        )

    h_direct_matrix = build_cyclic_filter_matrix(
        coefficients=h_vector,
        codeword_length=n,
        field=field,
    )

    g_direct_matrix = build_cyclic_filter_matrix(
        coefficients=g_vector,
        codeword_length=n,
        field=field,
    )

    j_matrix = build_shift_matrix(
        size=k,
        field=field,
        shift=shift,
    )

    h_inverse_matrix, g_inverse_matrix = build_inverse_wavelet_matrices(
        h_matrix=h_direct_matrix,
        g_matrix=g_direct_matrix,
        field=field,
    )

    check_wavelet_inverse_conditions(
        h_direct=h_direct_matrix,
        g_direct=g_direct_matrix,
        h_inverse=h_inverse_matrix,
        g_inverse=g_inverse_matrix,
        field=field,
    )

    # Математическая матрица G_C имеет размер n x k.
    generator_column_form = np.mod(
        h_direct_matrix.T
        + (a % field) * gf_matmul(g_direct_matrix.T, j_matrix, field),
        field,
    )

    # Для Python удобнее k x n:
    # codeword = message @ generator_matrix
    generator_matrix = generator_column_form.T

    if check_rank:
        rank = gf_rank(generator_matrix, field)

        if rank < k:
            raise ValueError(
                f"Порождающая матрица вырождена: rank = {rank}, а должен быть k = {k}. "
                f"Нужно выбрать другие коэффициенты h или параметр a."
            )

    parity_check_matrix = build_wavelet_parity_check_matrix(
        h_inverse=h_inverse_matrix,
        g_inverse=g_inverse_matrix,
        j_matrix=j_matrix,
        field=field,
        b=b,
        generator_matrix=generator_matrix,
    )

    components = {
        "h": h_vector,
        "g": g_vector,

        "H_direct": h_direct_matrix,
        "G_direct": g_direct_matrix,

        "H_inverse": h_inverse_matrix,
        "G_inverse": g_inverse_matrix,

        # Старые имена оставляем, чтобы не сломать main.py.
        "H_wavelet": h_direct_matrix,
        "G_wavelet": g_direct_matrix,

        "J": j_matrix,
        "a": a,
        "b": b,

        "G_C_column_form": generator_column_form,
        "generator_matrix": generator_matrix,
        "parity_check_matrix": parity_check_matrix,
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
            b: int = 1,
            shift: int = 1,
            name: str = "Wavelet code from scaling coefficients",
            g: Optional[Iterable[int]] = None,
    ) -> "WaveletCode":
        generator_matrix, components = build_wavelet_generator_matrix(
            h=h,
            g=g,
            codeword_length=codeword_length,
            field=field,
            a=a,
            b=b,
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