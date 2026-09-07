from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np
from bch import gf2_matrix_rank, to_binary_matrix
from .construction import (
    ReedSolomonConstruction,
    build_binary_parity_check_matrix,
    bits_to_symbols,
    symbols_to_bits,
)

@dataclass
class ReedSolomonBinaryCode:
    """Бинарный образ extended RS-кода, совместимый с research pipeline."""
    construction: ReedSolomonConstruction
    generator_matrix: np.ndarray
    parity_check_matrix: np.ndarray
    name: str = "Reed-Solomon binary"

    def __post_init__(self) -> None:
        self.generator_matrix = to_binary_matrix(self.generator_matrix, name="generator_matrix")
        self.parity_check_matrix = to_binary_matrix(self.parity_check_matrix, name="parity_check_matrix")
        if self.generator_matrix.shape != (self.binary_k, self.binary_n):
            raise ValueError("Размер G не соответствует binary-параметрам RS")
        if self.parity_check_matrix.shape != (self.binary_n - self.binary_k, self.binary_n):
            raise ValueError("Размер H не соответствует binary-параметрам RS")
        if gf2_matrix_rank(self.generator_matrix) != self.binary_k:
            raise ValueError("G RS binary не имеет полного ранга")
        if gf2_matrix_rank(self.parity_check_matrix) != self.binary_n - self.binary_k:
            raise ValueError("H RS binary не имеет полного ранга")
        product = (self.generator_matrix.astype(np.int64) @ self.parity_check_matrix.astype(np.int64).T) % 2
        if not np.all(product == 0):
            raise ValueError("G @ H.T должно быть нулевой матрицей над GF(2)")

    @property
    def n(self) -> int:
        return self.binary_n

    @property
    def k(self) -> int:
        return self.binary_k

    @property
    def binary_n(self) -> int:
        return self.construction.binary_n

    @property
    def binary_k(self) -> int:
        return self.construction.binary_k

    @property
    def code_rate(self) -> float:
        return self.k / self.n

    @property
    def field(self):
        return self.construction.field

    @property
    def evaluation_points(self) -> tuple[int, ...]:
        return self.construction.evaluation_points

    @property
    def column_multipliers(self) -> tuple[int, ...]:
        return self.construction.column_multipliers

    @classmethod
    def from_construction(cls, construction: ReedSolomonConstruction, name: str | None = None) -> "ReedSolomonBinaryCode":
        generator = construction.build_binary_generator_matrix()
        parity_check = build_binary_parity_check_matrix(generator)
        label = name or f"extended_RS_{construction.symbol_n}_{construction.symbol_k}_binary"
        return cls(construction=construction, generator_matrix=generator, parity_check_matrix=parity_check, name=label)

    @classmethod
    def from_parameters(cls, *, m: int, symbol_n: int, symbol_k: int, primitive_polynomial: int | None = None, evaluation_points: Iterable[int] | None = None, column_multipliers: Iterable[int] | None = None, name: str | None = None) -> "ReedSolomonBinaryCode":
        construction = ReedSolomonConstruction.create(m=m, symbol_n=symbol_n, symbol_k=symbol_k, primitive_polynomial=primitive_polynomial, evaluation_points=evaluation_points, column_multipliers=column_multipliers)
        return cls.from_construction(construction, name=name)

    def encode(self, message: Iterable[int]) -> np.ndarray:
        vector = np.asarray(list(message), dtype=np.uint8)
        if vector.ndim != 1 or len(vector) != self.k:
            raise ValueError(f"Длина сообщения должна быть k={self.k}")
        if not np.all((vector == 0) | (vector == 1)):
            raise ValueError("message должен содержать только 0 и 1")
        return ((vector.astype(np.int64) @ self.generator_matrix.astype(np.int64)) % 2).astype(np.uint8)

    def encode_symbols(self, message_symbols: Iterable[int]) -> np.ndarray:
        return self.construction.encode_symbols(message_symbols)

    def message_bits_to_symbols(self, message_bits: Iterable[int]) -> np.ndarray:
        return bits_to_symbols(message_bits, self.field.m)

    def codeword_symbols_to_bits(self, codeword_symbols: Iterable[int]) -> np.ndarray:
        return symbols_to_bits(codeword_symbols, self.field)

    def syndrome(self, word: Iterable[int]) -> np.ndarray:
        vector = np.asarray(list(word), dtype=np.uint8)
        if vector.ndim != 1 or len(vector) != self.n:
            raise ValueError(f"Длина слова должна быть n={self.n}")
        if not np.all((vector == 0) | (vector == 1)):
            raise ValueError("word должен содержать только 0 и 1")
        return ((self.parity_check_matrix.astype(np.int64) @ vector.astype(np.int64)) % 2).astype(np.uint8)

    def is_codeword(self, word: Iterable[int]) -> bool:
        return bool(np.all(self.syndrome(word) == 0))
