from dataclasses import dataclass
from itertools import combinations
from math import comb
from collections.abc import Iterator

import numpy as np

from .matrices import to_binary_matrix


@dataclass(frozen=True)
class SyndromeCollision:
    """
    Две различные ошибки, имеющие одинаковый синдром.

    Их сумма над GF(2) является ненулевым кодовым словом.
    """

    syndrome: int

    first_error_positions: tuple[int, ...]
    second_error_positions: tuple[int, ...]

    @property
    def codeword_positions(self) -> tuple[int, ...]:
        """
        Поддержка кодового слова:

            e_1 + e_2
        """
        positions = (
            set(self.first_error_positions)
            ^ set(self.second_error_positions)
        )

        return tuple(sorted(positions))

    @property
    def codeword_weight(self) -> int:
        return len(self.codeword_positions)


@dataclass(frozen=True)
class SyndromeCollisionAnalysis:
    """
    Результат проверки таблицы синдромов.
    """

    codeword_length: int
    syndrome_bits: int
    max_error_weight: int

    expected_pattern_count: int
    tested_pattern_count: int
    unique_syndrome_count: int
    repeated_syndrome_count: int

    completed: bool

    first_collision: SyndromeCollision | None

    @property
    def collision_free(self) -> bool:
        """
        True только если проверены все шаблоны
        и коллизий не обнаружено.
        """
        return (
            self.completed
            and self.repeated_syndrome_count == 0
        )

    @property
    def guaranteed_minimum_distance_lower_bound(
        self,
    ) -> int | None:
        """
        Если все ошибки веса <= t имеют разные синдромы,
        то:

            d_min >= 2*t + 1
        """
        if not self.collision_free:
            return None

        return 2 * self.max_error_weight + 1

    @property
    def guaranteed_error_correction(self) -> int | None:
        if not self.collision_free:
            return None

        return self.max_error_weight


def count_error_patterns(
    codeword_length: int,
    max_error_weight: int,
) -> int:
    """
    Число ошибок веса от 0 до max_error_weight.
    """
    if not isinstance(codeword_length, int):
        raise TypeError(
            "codeword_length должен быть целым числом"
        )

    if not isinstance(max_error_weight, int):
        raise TypeError(
            "max_error_weight должен быть целым числом"
        )

    if codeword_length <= 0:
        raise ValueError(
            "codeword_length должен быть положительным"
        )

    if max_error_weight < 0:
        raise ValueError(
            "max_error_weight не может быть отрицательным"
        )

    if max_error_weight > codeword_length:
        raise ValueError(
            "max_error_weight не может быть больше "
            "длины кодового слова"
        )

    return sum(
        comb(codeword_length, weight)
        for weight in range(max_error_weight + 1)
    )


def iter_error_patterns(
    codeword_length: int,
    max_error_weight: int,
) -> Iterator[tuple[int, ...]]:
    """
    Генерирует позиции единиц всех ошибок веса 0...t.
    """
    count_error_patterns(
        codeword_length=codeword_length,
        max_error_weight=max_error_weight,
    )

    for weight in range(max_error_weight + 1):
        yield from combinations(
            range(codeword_length),
            weight,
        )


def pack_parity_check_columns(
    parity_check_matrix: object,
) -> tuple[int, ...]:
    """
    Упаковывает каждый столбец H в целое число.

    Благодаря этому синдром ошибки можно вычислять
    как XOR соответствующих столбцов.
    """
    matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    row_count, column_count = matrix.shape

    packed_columns: list[int] = []

    for column in range(column_count):
        packed_value = 0

        for row in range(row_count):
            if matrix[row, column] == 1:
                packed_value |= 1 << row

        packed_columns.append(packed_value)

    return tuple(packed_columns)


def calculate_error_pattern_syndrome(
    error_positions: tuple[int, ...],
    packed_columns: tuple[int, ...],
) -> int:
    """
    Вычисляет синдром ошибки как XOR столбцов H.
    """
    syndrome = 0

    for position in error_positions:
        if position < 0 or position >= len(packed_columns):
            raise ValueError(
                f"Недопустимая позиция ошибки: {position}"
            )

        syndrome ^= packed_columns[position]

    return syndrome


def _find_previous_pattern_with_syndrome(
    target_syndrome: int,
    second_pattern: tuple[int, ...],
    packed_columns: tuple[int, ...],
    max_error_weight: int,
) -> tuple[int, ...] | None:
    """
    Повторно проходит ранее проверенные шаблоны,
    чтобы восстановить первый участник коллизии.

    Это позволяет основной проверке хранить только set синдромов,
    а не большой словарь syndrome -> pattern.
    """
    for candidate in iter_error_patterns(
        codeword_length=len(packed_columns),
        max_error_weight=max_error_weight,
    ):
        if candidate == second_pattern:
            break

        syndrome = calculate_error_pattern_syndrome(
            error_positions=candidate,
            packed_columns=packed_columns,
        )

        if syndrome == target_syndrome:
            return candidate

    return None


def analyze_syndrome_collisions(
    parity_check_matrix: object,
    max_error_weight: int,
    stop_after_first_collision: bool = False,
) -> SyndromeCollisionAnalysis:
    """
    Проверяет уникальность синдромов всех ошибок веса 0...t.

    Если коллизий нет, код гарантированно исправляет
    все ошибки веса не больше t.

    Если коллизия есть:

        H * e_1.T = H * e_2.T

    тогда:

        H * (e_1 + e_2).T = 0

    Следовательно, e_1 + e_2 является ненулевым
    кодовым словом веса не больше 2*t.
    """
    matrix = to_binary_matrix(
        parity_check_matrix,
        name="parity_check_matrix",
    )

    syndrome_bits, codeword_length = matrix.shape

    expected_pattern_count = count_error_patterns(
        codeword_length=codeword_length,
        max_error_weight=max_error_weight,
    )

    packed_columns = pack_parity_check_columns(
        matrix
    )

    seen_syndromes: set[int] = set()

    tested_pattern_count = 0
    repeated_syndrome_count = 0

    first_collision: SyndromeCollision | None = None

    for error_positions in iter_error_patterns(
        codeword_length=codeword_length,
        max_error_weight=max_error_weight,
    ):
        syndrome = calculate_error_pattern_syndrome(
            error_positions=error_positions,
            packed_columns=packed_columns,
        )

        tested_pattern_count += 1

        if syndrome not in seen_syndromes:
            seen_syndromes.add(syndrome)
            continue

        repeated_syndrome_count += 1

        if first_collision is None:
            previous_pattern = (
                _find_previous_pattern_with_syndrome(
                    target_syndrome=syndrome,
                    second_pattern=error_positions,
                    packed_columns=packed_columns,
                    max_error_weight=max_error_weight,
                )
            )

            if previous_pattern is None:
                raise RuntimeError(
                    "Обнаружена коллизия, но не удалось "
                    "восстановить первый шаблон ошибки"
                )

            first_collision = SyndromeCollision(
                syndrome=syndrome,
                first_error_positions=previous_pattern,
                second_error_positions=error_positions,
            )

        if stop_after_first_collision:
            break

    completed = (
        tested_pattern_count
        == expected_pattern_count
    )

    return SyndromeCollisionAnalysis(
        codeword_length=codeword_length,
        syndrome_bits=syndrome_bits,
        max_error_weight=max_error_weight,
        expected_pattern_count=expected_pattern_count,
        tested_pattern_count=tested_pattern_count,
        unique_syndrome_count=len(seen_syndromes),
        repeated_syndrome_count=(
            repeated_syndrome_count
        ),
        completed=completed,
        first_collision=first_collision,
    )


def syndrome_integer_to_bits(
    syndrome: int,
    bit_count: int,
) -> np.ndarray:
    """
    Преобразует упакованный синдром обратно
    в бинарный вектор.
    """
    if syndrome < 0:
        raise ValueError(
            "syndrome не может быть отрицательным"
        )

    if bit_count <= 0:
        raise ValueError(
            "bit_count должен быть положительным"
        )

    return np.asarray(
        [
            (syndrome >> index) & 1
            for index in range(bit_count)
        ],
        dtype=np.uint8,
    )