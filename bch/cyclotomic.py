def validate_binary_cyclotomic_code_length(
    code_length: int,
) -> int:
    """
    Проверяет модуль, по которому строятся двоичные
    циклотомические классы.

    Для примитивного бинарного BCH-кода:

        n = 2^m - 1

    Поэтому n всегда является положительным нечётным числом.
    """
    if not isinstance(code_length, int):
        raise TypeError(
            "code_length должен быть целым числом"
        )

    if code_length <= 0:
        raise ValueError(
            "code_length должен быть положительным"
        )

    if code_length % 2 == 0:
        raise ValueError(
            "Для бинарных примитивных BCH-кодов "
            "code_length должен быть нечётным"
        )

    return code_length


def build_binary_cyclotomic_coset(
    exponent: int,
    code_length: int,
) -> tuple[int, ...]:
    """
    Строит двоичный циклотомический класс показателя exponent
    по модулю code_length.

    Класс строится последовательным умножением на 2:

        C_i = {
            i,
            2i mod n,
            2^2 i mod n,
            ...
        }

    Построение прекращается, когда показатель начинает повторяться.
    """
    code_length = validate_binary_cyclotomic_code_length(
        code_length
    )

    if not isinstance(exponent, int):
        raise TypeError(
            "exponent должен быть целым числом"
        )

    normalized_exponent = exponent % code_length

    coset: list[int] = []
    current = normalized_exponent

    while current not in coset:
        coset.append(current)
        current = (2 * current) % code_length

    return tuple(coset)


def canonicalize_binary_cyclotomic_coset(
    coset: tuple[int, ...],
) -> tuple[int, ...]:
    """
    Возвращает каноническое представление класса.

    Один и тот же класс может быть построен от разных элементов:

        C_1 = (1, 2, 4, 8)
        C_2 = (2, 4, 8, 1)

    Для сравнения используем отсортированное представление.
    """
    if not coset:
        raise ValueError(
            "Циклотомический класс не должен быть пустым"
        )

    return tuple(sorted(set(coset)))


def build_all_binary_cyclotomic_cosets(
    code_length: int,
) -> tuple[tuple[int, ...], ...]:
    """
    Строит все различные двоичные циклотомические классы
    по модулю code_length.
    """
    code_length = validate_binary_cyclotomic_code_length(
        code_length
    )

    cosets: list[tuple[int, ...]] = []
    visited: set[int] = set()

    for exponent in range(code_length):
        if exponent in visited:
            continue

        coset = build_binary_cyclotomic_coset(
            exponent=exponent,
            code_length=code_length,
        )

        cosets.append(coset)
        visited.update(coset)

    return tuple(cosets)


def find_binary_cyclotomic_coset(
    exponent: int,
    code_length: int,
) -> tuple[int, ...]:
    """
    Возвращает циклотомический класс,
    содержащий заданный показатель.

    Фактически класс можно сразу построить от этого показателя.
    """
    return build_binary_cyclotomic_coset(
        exponent=exponent,
        code_length=code_length,
    )