from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from .code import BCHCode, to_binary_vector
from .matrices import (
    gf2_matrix_rank,
    to_binary_matrix,
    validate_bch_matrices,
)


@dataclass
class SystematicGeneratorResult:
    """
    Результат приведения порождающей матрицы
    к систематическому виду:

        G_systematic = [I_k | P]

    column_permutation[new_position] содержит номер
    соответствующей координаты в исходной матрице.
    """

    generator_matrix: np.ndarray
    column_permutation: tuple[int, ...]
    inverse_column_permutation: tuple[int, ...]

    def __post_init__(self) -> None:
        self.generator_matrix = to_binary_matrix(
            self.generator_matrix,
            name="generator_matrix",
        )

        _, n = self.generator_matrix.shape

        expected_coordinates = tuple(range(n))

        if tuple(sorted(self.column_permutation)) != (
            expected_coordinates
        ):
            raise ValueError(
                "column_permutation должна быть перестановкой "
                "всех координат кода"
            )

        if tuple(sorted(self.inverse_column_permutation)) != (
            expected_coordinates
        ):
            raise ValueError(
                "inverse_column_permutation должна быть "
                "перестановкой всех координат кода"
            )


def validate_systematic_generator_matrix(
    generator_matrix: object,
) -> np.ndarray:
    """
    Проверяет, что матрица имеет систематический вид:

        G = [I_k | P]
    """
    matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    )

    k, n = matrix.shape

    if k <= 0:
        raise ValueError(
            "Порождающая матрица не должна быть пустой"
        )

    if k >= n:
        raise ValueError(
            "Для линейного кода должно выполняться k < n"
        )

    identity = np.eye(
        k,
        dtype=np.uint8,
    )

    if not np.array_equal(
        matrix[:, :k],
        identity,
    ):
        raise ValueError(
            "Матрица не находится в систематическом виде "
            "[I_k | P]"
        )

    if gf2_matrix_rank(matrix) != k:
        raise ValueError(
            "Систематическая матрица должна иметь "
            "полный строковый ранг"
        )

    return matrix


def build_systematic_generator_matrix(
    generator_matrix: object,
) -> SystematicGeneratorResult:
    """
    Приводит полную по строковому рангу бинарную матрицу G
    к систематическому виду:

        [I_k | P]

    Используются:

        1. перестановки строк;
        2. сложение строк над GF(2);
        3. перестановки столбцов.

    Перестановка столбцов меняет только порядок координат
    кодового слова и не меняет параметры линейного кода.
    """
    matrix = to_binary_matrix(
        generator_matrix,
        name="generator_matrix",
    ).copy()

    k, n = matrix.shape

    if k >= n:
        raise ValueError(
            "Для линейного кода должно выполняться k < n"
        )

    rank = gf2_matrix_rank(matrix)

    if rank != k:
        raise ValueError(
            "Порождающая матрица должна иметь полный "
            f"строковый ранг: rank = {rank}, k = {k}"
        )

    column_permutation = np.arange(
        n,
        dtype=int,
    )

    for pivot_index in range(k):
        selected_row: int | None = None
        selected_column: int | None = None

        # Ищем любой ненулевой элемент в ещё не обработанной
        # части матрицы.
        for column in range(
            pivot_index,
            n,
        ):
            candidate_rows = np.flatnonzero(
                matrix[pivot_index:, column]
            )

            if candidate_rows.size == 0:
                continue

            selected_row = (
                pivot_index
                + int(candidate_rows[0])
            )

            selected_column = column
            break

        if (
            selected_row is None
            or selected_column is None
        ):
            raise ValueError(
                "Не удалось построить систематическую "
                "порождающую матрицу"
            )

        if selected_row != pivot_index:
            matrix[
                [pivot_index, selected_row]
            ] = matrix[
                [selected_row, pivot_index]
            ]

        if selected_column != pivot_index:
            matrix[
                :,
                [pivot_index, selected_column],
            ] = matrix[
                :,
                [selected_column, pivot_index],
            ]

            column_permutation[
                [pivot_index, selected_column]
            ] = column_permutation[
                [selected_column, pivot_index]
            ]

        # Обнуляем выбранный столбец во всех остальных строках.
        for row in range(k):
            if row == pivot_index:
                continue

            if matrix[row, pivot_index] == 1:
                matrix[row] ^= matrix[pivot_index]

    validate_systematic_generator_matrix(matrix)

    inverse_permutation = np.empty(
        n,
        dtype=int,
    )

    inverse_permutation[
        column_permutation
    ] = np.arange(
        n,
        dtype=int,
    )

    return SystematicGeneratorResult(
        generator_matrix=matrix,
        column_permutation=tuple(
            int(value)
            for value in column_permutation
        ),
        inverse_column_permutation=tuple(
            int(value)
            for value in inverse_permutation
        ),
    )


def shorten_systematic_generator_matrix(
    generator_matrix: object,
    shortening_count: int,
) -> np.ndarray:
    """
    Укорачивает систематический линейный код.

    Для:

        G = [I_k | P]

    первые shortening_count информационных символов
    фиксируются равными нулю.

    После этого удаляются:

        1. соответствующие строки G;
        2. соответствующие информационные столбцы.

    Параметры меняются так:

        [n, k] -> [n-s, k-s]
    """
    matrix = validate_systematic_generator_matrix(
        generator_matrix
    )

    if not isinstance(shortening_count, int):
        raise TypeError(
            "shortening_count должен быть целым числом"
        )

    if shortening_count < 0:
        raise ValueError(
            "shortening_count не может быть отрицательным"
        )

    k, _ = matrix.shape

    if shortening_count >= k:
        raise ValueError(
            "После укорочения должна остаться хотя бы "
            "одна информационная координата"
        )

    if shortening_count == 0:
        return matrix.copy()

    shortened_matrix = matrix[
        shortening_count:,
        shortening_count:,
    ].copy()

    validate_systematic_generator_matrix(
        shortened_matrix
    )

    return shortened_matrix


def puncture_systematic_generator_matrix(
    generator_matrix: object,
    puncture_count: int,
) -> np.ndarray:
    """
    Выкалывает последние puncture_count проверочных координат.

    Информационная часть I_k не затрагивается, поэтому
    размерность кода сохраняется.

    Параметры меняются так:

        [n, k] -> [n-p, k]
    """
    matrix = validate_systematic_generator_matrix(
        generator_matrix
    )

    if not isinstance(puncture_count, int):
        raise TypeError(
            "puncture_count должен быть целым числом"
        )

    if puncture_count < 0:
        raise ValueError(
            "puncture_count не может быть отрицательным"
        )

    k, n = matrix.shape
    parity_count = n - k

    if puncture_count > parity_count:
        raise ValueError(
            "Эта реализация может выкалывать только "
            "проверочные координаты"
        )

    if puncture_count == 0:
        return matrix.copy()

    punctured_matrix = matrix[
        :,
        :n - puncture_count,
    ].copy()

    validate_systematic_generator_matrix(
        punctured_matrix
    )

    return punctured_matrix


def build_systematic_parity_check_matrix(
    generator_matrix: object,
) -> np.ndarray:
    """
    Строит проверочную матрицу для систематической G.

    Если:

        G = [I_k | P],

    то над GF(2):

        H = [P.T | I_(n-k)]

    и:

        G @ H.T = 0.
    """
    generator = validate_systematic_generator_matrix(
        generator_matrix
    )

    k, n = generator.shape
    redundancy = n - k

    parity_part = generator[:, k:]

    parity_check_matrix = np.hstack(
        (
            parity_part.T,
            np.eye(
                redundancy,
                dtype=np.uint8,
            ),
        )
    ).astype(np.uint8)

    validate_bch_matrices(
        generator_matrix=generator,
        parity_check_matrix=parity_check_matrix,
    )

    return parity_check_matrix


@dataclass
class BCHDerivedCode:
    """
    BCH-производный бинарный линейный код.

    Код строится из примитивного BCH-кода:

        1. приведением G к систематическому виду;
        2. укорочением информационных координат;
        3. выкалыванием проверочных координат.

    Конечная G остаётся систематической:

        G = [I_k | P].
    """

    parent_code: BCHCode

    generator_matrix: np.ndarray
    parity_check_matrix: np.ndarray

    shortening_count: int
    puncture_count: int

    minimum_distance_lower_bound: int

    parent_systematic_column_permutation: tuple[
        int,
        ...,
    ]

    shortened_parent_coordinates: tuple[
        int,
        ...,
    ]

    punctured_parent_coordinates: tuple[
        int,
        ...,
    ]

    remaining_parent_coordinates: tuple[
        int,
        ...,
    ]

    name: str = "BCH-derived code"

    def __post_init__(self) -> None:
        self.generator_matrix = (
            validate_systematic_generator_matrix(
                self.generator_matrix
            )
        )

        self.parity_check_matrix = to_binary_matrix(
            self.parity_check_matrix,
            name="parity_check_matrix",
        )

        validate_bch_matrices(
            generator_matrix=self.generator_matrix,
            parity_check_matrix=self.parity_check_matrix,
        )

        expected_k = (
            self.parent_code.k
            - self.shortening_count
        )

        expected_n = (
            self.parent_code.n
            - self.shortening_count
            - self.puncture_count
        )

        if self.k != expected_k:
            raise ValueError(
                "Размерность производного кода не соответствует "
                "числу укороченных координат"
            )

        if self.n != expected_n:
            raise ValueError(
                "Длина производного кода не соответствует "
                "укорочению и выкалыванию"
            )

        if len(self.remaining_parent_coordinates) != self.n:
            raise ValueError(
                "Количество оставшихся родительских координат "
                "должно совпадать с n"
            )

        all_parent_coordinates = (
            self.shortened_parent_coordinates
            + self.punctured_parent_coordinates
            + self.remaining_parent_coordinates
        )

        if tuple(
            sorted(all_parent_coordinates)
        ) != tuple(
            range(self.parent_code.n)
        ):
            raise ValueError(
                "Родительские координаты учтены некорректно"
            )

    @classmethod
    def from_primitive_parent(
        cls,
        m: int,
        designed_distance: int,
        shortening_count: int,
        puncture_count: int,
        primitive_polynomial: int | None = None,
        first_root: int = 1,
        name: str | None = None,
    ) -> "BCHDerivedCode":
        """
        Строит BCH-производный код из примитивного BCH-кода.
        """
        parent_code = BCHCode.primitive(
            m=m,
            designed_distance=designed_distance,
            primitive_polynomial=primitive_polynomial,
            first_root=first_root,
            name=(
                f"Parent BCH("
                f"{(1 << m) - 1}, "
                f"delta={designed_distance}"
                f")"
            ),
        )

        systematic_result = (
            build_systematic_generator_matrix(
                parent_code.generator_matrix
            )
        )

        shortened_generator = (
            shorten_systematic_generator_matrix(
                generator_matrix=(
                    systematic_result.generator_matrix
                ),
                shortening_count=shortening_count,
            )
        )

        shortened_n = shortened_generator.shape[1]

        punctured_generator = (
            puncture_systematic_generator_matrix(
                generator_matrix=shortened_generator,
                puncture_count=puncture_count,
            )
        )

        parity_check_matrix = (
            build_systematic_parity_check_matrix(
                punctured_generator
            )
        )

        systematic_parent_coordinates = (
            systematic_result.column_permutation
        )

        shortened_parent_coordinates = (
            systematic_parent_coordinates[
                :shortening_count
            ]
        )

        parent_coordinates_after_shortening = (
            systematic_parent_coordinates[
                shortening_count:
            ]
        )

        if puncture_count == 0:
            punctured_parent_coordinates: tuple[
                int,
                ...,
            ] = ()

            remaining_parent_coordinates = (
                parent_coordinates_after_shortening
            )
        else:
            punctured_parent_coordinates = (
                parent_coordinates_after_shortening[
                    shortened_n - puncture_count:
                ]
            )

            remaining_parent_coordinates = (
                parent_coordinates_after_shortening[
                    :shortened_n - puncture_count
                ]
            )

        # Укорочение не уменьшает минимальное расстояние.
        # Каждое выкалывание может уменьшить его максимум на 1.
        minimum_distance_lower_bound = max(
            1,
            designed_distance - puncture_count,
        )

        resolved_name = name

        if resolved_name is None:
            resolved_name = (
                f"BCH-derived("
                f"{punctured_generator.shape[1]}, "
                f"{punctured_generator.shape[0]}, "
                f"d>={minimum_distance_lower_bound}"
                f")"
            )

        return cls(
            parent_code=parent_code,
            generator_matrix=punctured_generator,
            parity_check_matrix=parity_check_matrix,
            shortening_count=shortening_count,
            puncture_count=puncture_count,
            minimum_distance_lower_bound=(
                minimum_distance_lower_bound
            ),
            parent_systematic_column_permutation=(
                systematic_parent_coordinates
            ),
            shortened_parent_coordinates=(
                shortened_parent_coordinates
            ),
            punctured_parent_coordinates=(
                punctured_parent_coordinates
            ),
            remaining_parent_coordinates=(
                remaining_parent_coordinates
            ),
            name=resolved_name,
        )

    @property
    def n(self) -> int:
        return int(
            self.generator_matrix.shape[1]
        )

    @property
    def k(self) -> int:
        return int(
            self.generator_matrix.shape[0]
        )

    @property
    def code_rate(self) -> float:
        return self.k / self.n

    @property
    def guaranteed_error_correction(self) -> int:
        """
        Гарантированный радиус уникального декодирования,
        следующий из нижней границы расстояния.
        """
        return (
            self.minimum_distance_lower_bound - 1
        ) // 2

    def encode(
        self,
        message: Iterable[int],
    ) -> np.ndarray:
        """
        Кодирует сообщение:

            codeword = message @ G mod 2.
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
        Вычисляет бинарный синдром принятого слова.
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
            word.astype(np.int64)
            @ self.parity_check_matrix.astype(
                np.int64
            ).T,
            2,
        )

        return syndrome.astype(np.uint8)

    def is_codeword(
        self,
        word: Iterable[int],
    ) -> bool:
        """
        Проверяет нулевой синдром слова.
        """
        return bool(
            np.all(
                self.syndrome(word) == 0
            )
        )

    def extract_message(
        self,
        codeword: Iterable[int],
    ) -> np.ndarray:
        """
        Извлекает сообщение из корректного кодового слова.

        Поскольку G находится в систематическом виде,
        первые k координат являются информационными.
        """
        word = to_binary_vector(
            codeword,
            name="codeword",
        )

        if len(word) != self.n:
            raise ValueError(
                f"Длина кодового слова должна быть n = {self.n}, "
                f"получено {len(word)}"
            )

        if not self.is_codeword(word):
            raise ValueError(
                "Переданное слово не является "
                "кодовым словом"
            )

        return word[:self.k].copy()