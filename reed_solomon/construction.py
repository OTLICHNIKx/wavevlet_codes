from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np
from bch import GF2m, create_gf2m

def _bits(values: Iterable[int], length: int, name: str) -> np.ndarray:
    vector = np.asarray(list(values), dtype=np.uint8)
    if vector.ndim != 1 or len(vector) != length:
        raise ValueError(f"{name} должен иметь длину {length}")
    if not np.all((vector == 0) | (vector == 1)):
        raise ValueError(f"{name} должен содержать только 0 и 1")
    return vector

def bits_to_symbols(bits: Iterable[int], m: int) -> np.ndarray:
    vector = np.asarray(list(bits), dtype=np.uint8)
    if m <= 0 or vector.ndim != 1 or len(vector) % m != 0:
        raise ValueError("Длина bits должна быть кратна положительному m")
    if not np.all((vector == 0) | (vector == 1)):
        raise ValueError("bits должен содержать только 0 и 1")
    symbols = np.zeros(len(vector) // m, dtype=np.int64)
    for index, bit in enumerate(vector):
        symbols[index // m] |= int(bit) << (index % m)
    return symbols

def symbols_to_bits(symbols: Iterable[int], field: GF2m) -> np.ndarray:
    values = [field.validate_element(int(value), name="symbol") for value in symbols]
    result = np.zeros(len(values) * field.m, dtype=np.uint8)
    for symbol_index, value in enumerate(values):
        for bit_index in range(field.m):
            result[symbol_index * field.m + bit_index] = (value >> bit_index) & 1
    return result

def default_evaluation_points(field: GF2m, symbol_n: int) -> tuple[int, ...]:
    if symbol_n <= 0 or symbol_n > field.size:
        raise ValueError(f"Для extended GRS допустимо 1 <= N <= {field.size}")
    return (0,) + tuple(field.alpha(exponent) for exponent in range(symbol_n - 1))

@dataclass(frozen=True)
class ReedSolomonConstruction:
    """Детерминированная GRS(N,K) конструкция над GF(2^m)."""
    field: GF2m
    symbol_n: int
    symbol_k: int
    evaluation_points: tuple[int, ...]
    column_multipliers: tuple[int, ...]

    def __post_init__(self) -> None:
        if not 0 < self.symbol_k < self.symbol_n:
            raise ValueError("Для GRS требуется 0 < symbol_k < symbol_n")
        if len(self.evaluation_points) != self.symbol_n:
            raise ValueError("Число evaluation points должно совпадать с symbol_n")
        if len(self.column_multipliers) != self.symbol_n:
            raise ValueError("Число column multipliers должно совпадать с symbol_n")
        points = tuple(self.field.validate_element(int(value), name="evaluation_point") for value in self.evaluation_points)
        multipliers = tuple(self.field.validate_element(int(value), name="column_multiplier") for value in self.column_multipliers)
        if len(set(points)) != len(points):
            raise ValueError("Evaluation points GRS должны быть уникальны")
        if any(value == 0 for value in multipliers):
            raise ValueError("Column multipliers GRS должны быть ненулевыми")
        object.__setattr__(self, "evaluation_points", points)
        object.__setattr__(self, "column_multipliers", multipliers)

    @property
    def binary_n(self) -> int:
        return self.symbol_n * self.field.m

    @property
    def binary_k(self) -> int:
        return self.symbol_k * self.field.m

    @classmethod
    def create(cls, *, m: int, symbol_n: int, symbol_k: int, primitive_polynomial: int | None = None, evaluation_points: Iterable[int] | None = None, column_multipliers: Iterable[int] | None = None) -> "ReedSolomonConstruction":
        field = create_gf2m(m=m, primitive_polynomial=primitive_polynomial)
        points = default_evaluation_points(field, symbol_n) if evaluation_points is None else tuple(int(value) for value in evaluation_points)
        multipliers = (1,) * symbol_n if column_multipliers is None else tuple(int(value) for value in column_multipliers)
        return cls(field=field, symbol_n=symbol_n, symbol_k=symbol_k, evaluation_points=points, column_multipliers=multipliers)

    def encode_symbols(self, message_symbols: Iterable[int]) -> np.ndarray:
        message = [self.field.validate_element(int(value), name="message_symbol") for value in message_symbols]
        if len(message) != self.symbol_k:
            raise ValueError(f"Число информационных символов должно быть K={self.symbol_k}")
        codeword = np.zeros(self.symbol_n, dtype=np.int64)
        for index, point in enumerate(self.evaluation_points):
            value = 0
            for coefficient in reversed(message):
                value = self.field.add(self.field.multiply(value, point), coefficient)
            codeword[index] = self.field.multiply(self.column_multipliers[index], value)
        return codeword

    def encode_bits(self, message_bits: Iterable[int]) -> np.ndarray:
        message = _bits(message_bits, self.binary_k, "message_bits")
        return symbols_to_bits(self.encode_symbols(bits_to_symbols(message, self.field.m)), self.field)

    def build_binary_generator_matrix(self) -> np.ndarray:
        generator = np.zeros((self.binary_k, self.binary_n), dtype=np.uint8)
        for row in range(self.binary_k):
            message = np.zeros(self.binary_k, dtype=np.uint8)
            message[row] = 1
            generator[row] = self.encode_bits(message)
        return generator

def gf2_nullspace_basis(matrix: object) -> np.ndarray:
    reduced = np.asarray(matrix, dtype=np.uint8).copy()
    if reduced.ndim != 2 or not np.all((reduced == 0) | (reduced == 1)):
        raise ValueError("matrix должна быть бинарной двумерной матрицей")
    rows, columns = reduced.shape
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

def build_binary_parity_check_matrix(generator_matrix: object) -> np.ndarray:
    return gf2_nullspace_basis(generator_matrix)
