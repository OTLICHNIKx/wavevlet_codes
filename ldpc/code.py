from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .construction import (
    generator_from_parity_check,
    matrix_from_hex_rows,
    trim_matrix_to_width,
    validate_ldpc_matrices,
    weight_profile,
)


def _build_from_hex_rows(
    generator_hex_rows: Sequence[str] | None,
    parity_check_hex_rows: Sequence[str],
    n: int,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Собирает (G, H) из замороженных hex-строк.

    H задаётся явно (именно она определяет LDPC-структуру),
    G восстанавливается как базис ядра H и приводится к форме
    с полным рангом k.
    """
    parity_check = trim_matrix_to_width(
        matrix_from_hex_rows(parity_check_hex_rows, name="H"),
        width=n,
        name="H",
    )
    if generator_hex_rows is None:
        generator = generator_from_parity_check(parity_check)
    else:
        generator = trim_matrix_to_width(
            matrix_from_hex_rows(generator_hex_rows, name="G"),
            width=n,
            name="G",
        )
    return validate_ldpc_matrices(generator, parity_check, n=n, k=k)


@dataclass
class LDPCCode:
    """
    LDPC-код как обычный линейный блочный код.

    Совместим с существующим research pipeline: предоставляет
    generator_matrix, parity_check_matrix, n, k, name и стандартные
    encode/syndrome/is_codeword. Отдельного LDPC-декодера не требует:
    декодирование идёт общими syndrome/Chase/MLD декодерами.
    """

    generator_matrix: np.ndarray
    parity_check_matrix: np.ndarray
    n: int
    k: int
    name: str = "LDPC code"

    def __post_init__(self) -> None:
        self.generator_matrix, self.parity_check_matrix = (
            validate_ldpc_matrices(
                self.generator_matrix,
                self.parity_check_matrix,
                n=self.n,
                k=self.k,
            )
        )
        self._parity_check_profile = weight_profile(
            self.parity_check_matrix, name="parity_check_matrix"
        )

    @property
    def G(self) -> np.ndarray:
        return self.generator_matrix

    @property
    def H(self) -> np.ndarray:
        return self.parity_check_matrix

    @property
    def code_rate(self) -> float:
        return self.k / self.n

    @property
    def parity_check_weight_profile(self) -> dict[str, float]:
        return dict(self._parity_check_profile)

    @classmethod
    def from_hex_rows(
        cls,
        *,
        parity_check_hex_rows: Sequence[str],
        n: int,
        k: int,
        name: str = "LDPC code",
        generator_hex_rows: Sequence[str] | None = None,
    ) -> "LDPCCode":
        generator, parity_check = _build_from_hex_rows(
            generator_hex_rows=generator_hex_rows,
            parity_check_hex_rows=parity_check_hex_rows,
            n=n,
            k=k,
        )
        return cls(
            generator_matrix=generator,
            parity_check_matrix=parity_check,
            n=n,
            k=k,
            name=name,
        )

    def encode(self, message: Iterable[int]) -> np.ndarray:
        vector = np.asarray(list(message), dtype=np.uint8)
        if vector.ndim != 1 or len(vector) != self.k:
            raise ValueError(f"Длина сообщения должна быть k={self.k}")
        if not np.all((vector == 0) | (vector == 1)):
            raise ValueError("message должен содержать только 0 и 1")
        return (
            (vector.astype(np.int64) @ self.generator_matrix.astype(np.int64)) % 2
        ).astype(np.uint8)

    def syndrome(self, word: Iterable[int]) -> np.ndarray:
        vector = np.asarray(list(word), dtype=np.uint8)
        if vector.ndim != 1 or len(vector) != self.n:
            raise ValueError(f"Длина слова должна быть n={self.n}")
        if not np.all((vector == 0) | (vector == 1)):
            raise ValueError("word должен содержать только 0 и 1")
        return (
            (self.parity_check_matrix.astype(np.int64) @ vector.astype(np.int64)) % 2
        ).astype(np.uint8)

    def is_codeword(self, word: Iterable[int]) -> bool:
        return bool(np.all(self.syndrome(word) == 0))
