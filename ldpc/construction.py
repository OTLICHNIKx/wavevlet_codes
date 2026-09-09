from __future__ import annotations

import itertools
import math
from typing import Iterable, Sequence

import numpy as np

from bch import gf2_matrix_rank, to_binary_matrix


def matrix_to_hex_rows(matrix: object) -> tuple[str, ...]:
    """Кодирует бинарную матрицу в компактные hex-строки (по строке за раз)."""
    binary = to_binary_matrix(matrix, name="matrix")
    rows: list[str] = []
    for row in binary:
        value = 0
        for bit in row:
            value = (value << 1) | int(bit)
        digits = (binary.shape[1] + 3) // 4
        rows.append(format(value, f"0{digits}x"))
    return tuple(rows)


def matrix_from_hex_rows(hex_rows: Sequence[str], name: str = "matrix") -> np.ndarray:
    """Декодирует hex-строки обратно в бинарную матрицу."""
    if not hex_rows:
        raise ValueError(f"{name} не может быть пустой")
    rows = [row.strip().lower() for row in hex_rows]
    lengths = {len(row) for row in rows}
    if len(lengths) != 1:
        raise ValueError(f"Все hex-строки {name} должны иметь одинаковую длину")
    width = next(iter(lengths))
    if any(not all(char in "0123456789abcdef" for char in row) for row in rows):
        raise ValueError(f"{name} содержит недопустимые hex-символы")
    columns = width * 4
    result = np.zeros((len(rows), columns), dtype=np.uint8)
    for row_index, row in enumerate(rows):
        value = int(row, 16)
        for column in range(columns):
            result[row_index, column] = (value >> (columns - 1 - column)) & 1
    return result


def trim_matrix_to_width(matrix: object, width: int, name: str = "matrix") -> np.ndarray:
    """Усекает лишние ведущие нулевые столбцы, добавленные hex-кодировкой."""
    binary = to_binary_matrix(matrix, name=name)
    if binary.shape[1] < width:
        raise ValueError(f"{name} уже, чем ожидаемая ширина {width}")
    if binary.shape[1] == width:
        return binary
    offset = binary.shape[1] - width
    if np.any(binary[:, :offset] != 0):
        raise ValueError(f"{name} имеет ненулевые столбцы за пределами ширины {width}")
    return binary[:, offset:].copy()


def parity_check_from_generator(generator_matrix: object) -> np.ndarray:
    """Строит H полного ранга ((n-k) x n) как базис ядра G над GF(2)."""
    generator = to_binary_matrix(generator_matrix, name="generator_matrix")
    rows, columns = generator.shape
    reduced = generator.copy()
    pivots: list[int] = []
    pivot_row = 0
    for column in range(columns):
        if pivot_row >= rows:
            break
        candidates = np.flatnonzero(reduced[pivot_row:, column])
        if candidates.size == 0:
            continue
        selected = pivot_row + int(candidates[0])
        if selected != pivot_row:
            reduced[[pivot_row, selected]] = reduced[[selected, pivot_row]]
        for row in range(rows):
            if row != pivot_row and reduced[row, column] == 1:
                reduced[row] ^= reduced[pivot_row]
        pivots.append(column)
        pivot_row += 1
    free_columns = [column for column in range(columns) if column not in set(pivots)]
    basis = np.zeros((len(free_columns), columns), dtype=np.uint8)
    for basis_row, free_column in enumerate(free_columns):
        basis[basis_row, free_column] = 1
        for row, pivot_column in enumerate(pivots):
            basis[basis_row, pivot_column] = reduced[row, free_column]
    return basis


def generator_from_parity_check(parity_check_matrix: object) -> np.ndarray:
    """Строит G полного ранга (k x n) как базис ядра H над GF(2)."""
    return parity_check_from_generator(parity_check_matrix)


def validate_ldpc_matrices(
    generator_matrix: object,
    parity_check_matrix: object,
    *,
    n: int,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Полная проверка пары G/H для LDPC-кода [n, k].

    Проверяет размеры, ранги и ортогональность G @ H.T = 0 mod 2.
    Возвращает приведённые к uint8 матрицы.
    """
    generator = to_binary_matrix(generator_matrix, name="generator_matrix")
    parity_check = to_binary_matrix(parity_check_matrix, name="parity_check_matrix")

    if generator.shape != (k, n):
        raise ValueError(
            f"generator_matrix должна иметь форму {(k, n)}, "
            f"получено {generator.shape}"
        )
    if parity_check.shape != (n - k, n):
        raise ValueError(
            f"parity_check_matrix должна иметь форму {(n - k, n)}, "
            f"получено {parity_check.shape}"
        )
    if gf2_matrix_rank(generator) != k:
        raise ValueError("G не имеет полного строкового ранга")
    if gf2_matrix_rank(parity_check) != n - k:
        raise ValueError("H не имеет полного строкового ранга")
    product = (
        generator.astype(np.int64) @ parity_check.astype(np.int64).T
    ) % 2
    if not np.all(product == 0):
        raise ValueError("G @ H.T должно быть нулевой матрицей над GF(2)")
    return generator, parity_check


def weight_profile(matrix: object, name: str = "matrix") -> dict[str, int]:
    """Возвращает min/max/avg профили весов строк и столбцов матрицы."""
    binary = to_binary_matrix(matrix, name=name)
    row_weights = binary.sum(axis=1)
    column_weights = binary.sum(axis=0)
    return {
        "min_row_weight": int(row_weights.min()),
        "max_row_weight": int(row_weights.max()),
        "avg_row_weight": float(row_weights.mean()),
        "min_column_weight": int(column_weights.min()),
        "max_column_weight": int(column_weights.max()),
        "avg_column_weight": float(column_weights.mean()),
        "density": float(binary.mean()),
    }


def exact_minimum_distance_by_enumeration(
    generator_matrix: object,
    *,
    max_k: int = 20,
) -> int:
    """
    Точное d_min полным перебором всех 2^k сообщений.

    Быстрая векторизованная реализация: строим все codewords
    Gray-порядком и считаем веса.
    """
    generator = to_binary_matrix(generator_matrix, name="generator_matrix")
    k, n = generator.shape
    if k > max_k:
        raise ValueError(f"Перебор поддержан только для k <= {max_k}, получено k={k}")
    total = 1 << k
    best = n + 1
    current = np.zeros(n, dtype=np.uint8)
    previous_gray = 0
    for counter in range(1, total):
        gray = counter ^ (counter >> 1)
        changed = previous_gray ^ gray
        bit = int(changed.bit_length() - 1)
        current ^= generator[bit]
        weight = int(np.count_nonzero(current))
        if 0 < weight < best:
            best = weight
        previous_gray = gray
    return best


def column_masks(parity_check_matrix: object) -> np.ndarray:
    """
    Столбцы H как int64-маски строк (требует rank-представление rows <= 62).
    """
    parity_check = to_binary_matrix(
        parity_check_matrix, name="parity_check_matrix"
    )
    if parity_check.shape[0] > 62:
        raise ValueError("Метод поддержан для H с числом строк <= 62")
    return np.array(
        [
            sum(int(bit) << row for row, bit in enumerate(parity_check[:, column]))
            for column in range(parity_check.shape[1])
        ],
        dtype=np.int64,
    )


def combination_index(columns: int, size: int) -> np.ndarray:
    """Матрица (C(columns,size), size) всех size-подмножеств столбцов."""
    return np.fromiter(
        itertools.chain.from_iterable(
            itertools.combinations(range(columns), size)
        ),
        dtype=np.intp,
        count=math.comb(columns, size) * size,
    ).reshape(-1, size)


def syndromes_for_combinations(
    masks: np.ndarray, combo: np.ndarray
) -> np.ndarray:
    """Синдромы (XOR масок) для предвычисленных комбинаций столбцов."""
    syndromes = np.zeros(combo.shape[0], dtype=np.int64)
    for position in range(combo.shape[1]):
        np.bitwise_xor(syndromes, masks[combo[:, position]], out=syndromes)
    return syndromes


def minimum_distance_certificate(parity_check_matrix: object, w: int) -> int:
    """
    Сертификат нижней границы d_min по синдромному методу.

    Если все подмножества столбцов H размера <= w имеют ненулевые
    попарно различные синдромы, то зависимых множеств веса <= 2w нет
    и возвращается 2w + 1; иначе возвращается 0 (граница 2w+1 данным
    методом не доказана; фактический d_min может быть любым <= 2w
    или больше — требуется другой анализ).
    """
    parity_check = to_binary_matrix(
        parity_check_matrix, name="parity_check_matrix"
    )
    if w < 1:
        raise ValueError("w должен быть положительным")
    masks = column_masks(parity_check)
    seen = np.zeros(0, dtype=np.int64)
    for size in range(1, w + 1):
        combo = combination_index(parity_check.shape[1], size)
        syndromes = syndromes_for_combinations(masks, combo)
        if np.any(syndromes == 0):
            return 0
        combined = np.sort(np.concatenate([seen, syndromes]))
        if combined.size > 1 and np.any(combined[1:] == combined[:-1]):
            return 0
        seen = combined
    return 2 * w + 1
