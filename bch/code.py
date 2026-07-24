from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from .generator import (
    BCHGeneratorResult,
    build_bch_generator_polynomial,
)

from .matrices import (
    BCHMatrices,
    build_bch_matrices,
    validate_bch_matrices,
)

from .polynomial import (
    coefficients_to_integer,
    gf2_polynomial_divmod,
    integer_to_coefficients,
)


def to_binary_vector(
    values: Iterable[int],
    name: str = "vector",
) -> np.ndarray:
    """
    Преобразует вход в одномерный бинарный вектор.
    """
    vector = np.asarray(list(values))

    if vector.ndim != 1:
        raise ValueError(
            f"{name} должен быть одномерным вектором"
        )

    if not np.all(
        (vector == 0) | (vector == 1)
    ):
        raise ValueError(
            f"{name} должен содержать только 0 и 1"
        )

    return vector.astype(np.uint8)


@dataclass
class BCHCode:
    """
    Примитивный бинарный BCH-код.

    Используется то же соглашение, что и в WaveletCode:

        generator_matrix имеет размер k x n;
        message имеет длину k;
        codeword = message @ generator_matrix mod 2.

    Порядок коэффициентов соответствует полиномам:

        message[0] — коэффициент при x^0;
        message[1] — коэффициент при x^1;
        ...
    """

    construction: BCHGeneratorResult
    matrices: BCHMatrices
    name: str = "BCH code"

    def __post_init__(self) -> None:
        if self.generator_matrix.shape != (
            self.k,
            self.n,
        ):
            raise ValueError(
                "Размер матрицы G не соответствует "
                "параметрам BCH-кода"
            )

        if self.parity_check_matrix.shape != (
            self.n - self.k,
            self.n,
        ):
            raise ValueError(
                "Размер матрицы H не соответствует "
                "параметрам BCH-кода"
            )

        validate_bch_matrices(
            generator_matrix=self.generator_matrix,
            parity_check_matrix=self.parity_check_matrix,
        )

    @classmethod
    def primitive(
        cls,
        m: int,
        designed_distance: int,
        primitive_polynomial: int | None = None,
        first_root: int = 1,
        name: str | None = None,
    ) -> "BCHCode":
        """
        Строит примитивный бинарный BCH-код.

        Длина кода:

            n = 2^m - 1
        """
        construction = (
            build_bch_generator_polynomial(
                m=m,
                designed_distance=designed_distance,
                primitive_polynomial=(
                    primitive_polynomial
                ),
                first_root=first_root,
            )
        )

        return cls.from_generator_result(
            construction=construction,
            name=name,
        )

    @classmethod
    def from_generator_result(
        cls,
        construction: BCHGeneratorResult,
        name: str | None = None,
    ) -> "BCHCode":
        """
        Создаёт BCHCode из ранее построенного
        порождающего полинома.
        """
        matrices = build_bch_matrices(
            construction
        )

        resolved_name = name

        if resolved_name is None:
            resolved_name = (
                f"Primitive BCH("
                f"{construction.n}, "
                f"{construction.k}, "
                f"delta={construction.designed_distance}"
                f")"
            )

        return cls(
            construction=construction,
            matrices=matrices,
            name=resolved_name,
        )

    @property
    def m(self) -> int:
        return self.construction.m

    @property
    def n(self) -> int:
        return self.construction.n

    @property
    def k(self) -> int:
        return self.construction.k

    @property
    def code_rate(self) -> float:
        return self.k / self.n

    @property
    def designed_distance(self) -> int:
        return self.construction.designed_distance

    @property
    def guaranteed_error_correction(self) -> int:
        return (
            self.construction
            .guaranteed_error_correction
        )

    @property
    def generator_polynomial(self) -> int:
        return (
            self.construction.generator_polynomial
        )

    @property
    def check_polynomial(self) -> int:
        return self.matrices.check_polynomial

    @property
    def dual_generator_polynomial(self) -> int:
        return (
            self.matrices
            .dual_generator_polynomial
        )

    @property
    def generator_matrix(self) -> np.ndarray:
        return self.matrices.generator_matrix

    @property
    def parity_check_matrix(self) -> np.ndarray:
        return self.matrices.parity_check_matrix

    def encode(
        self,
        message: Iterable[int],
    ) -> np.ndarray:
        """
        Кодирует сообщение длины k.

        Возвращает кодовое слово длины n.
        """
        message_vector = to_binary_vector(
            message,
            name="message",
        )

        if len(message_vector) != self.k:
            raise ValueError(
                f"Длина сообщения должна быть k = {self.k}, "
                f"получено {len(message_vector)}"
            )

        codeword = np.mod(
            message_vector.astype(np.int64)
            @ self.generator_matrix.astype(np.int64),
            2,
        )

        return codeword.astype(np.uint8)

    def syndrome(
        self,
        received_word: Iterable[int],
    ) -> np.ndarray:
        """
        Вычисляет синдром принятого слова:

            syndrome = H @ received_word.T mod 2
        """
        word = to_binary_vector(
            received_word,
            name="received_word",
        )

        if len(word) != self.n:
            raise ValueError(
                f"Длина слова должна быть n = {self.n}, "
                f"получено {len(word)}"
            )

        syndrome = np.mod(
            self.parity_check_matrix.astype(np.int64)
            @ word.astype(np.int64),
            2,
        )

        return syndrome.astype(np.uint8)

    def is_codeword(
        self,
        word: Iterable[int],
    ) -> bool:
        """
        Проверяет, является ли слово кодовым.
        """
        syndrome = self.syndrome(word)

        return bool(np.all(syndrome == 0))

    def extract_message(
        self,
        codeword: Iterable[int],
    ) -> np.ndarray:
        """
        Извлекает сообщение из корректного кодового слова.

        Это не декодер ошибок.

        Метод работает только тогда, когда codeword уже является
        корректным кодовым словом BCH.

        Поскольку:

            c(x) = m(x) * g(x)

        сообщение можно получить делением:

            m(x) = c(x) / g(x)
        """
        codeword_vector = to_binary_vector(
            codeword,
            name="codeword",
        )

        if len(codeword_vector) != self.n:
            raise ValueError(
                f"Длина кодового слова должна быть n = {self.n}, "
                f"получено {len(codeword_vector)}"
            )

        if not self.is_codeword(codeword_vector):
            raise ValueError(
                "Переданное слово не является "
                "корректным кодовым словом BCH"
            )

        codeword_polynomial = coefficients_to_integer(
            codeword_vector.tolist()
        )

        message_polynomial, remainder = (
            gf2_polynomial_divmod(
                dividend=codeword_polynomial,
                divisor=self.generator_polynomial,
            )
        )

        if remainder != 0:
            raise ValueError(
                "Кодовое слово не делится "
                "на порождающий полином"
            )

        if message_polynomial >> self.k:
            raise ValueError(
                "Степень восстановленного сообщения "
                "превышает допустимую"
            )

        message = integer_to_coefficients(
            polynomial=message_polynomial,
            min_length=self.k,
        )

        return np.asarray(
            message[:self.k],
            dtype=np.uint8,
        )