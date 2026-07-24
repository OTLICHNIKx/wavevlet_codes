from collections.abc import Iterable


def validate_binary_polynomial(
    polynomial: int,
    name: str = "polynomial",
) -> int:
    """
    Проверяет представление двоичного полинома.
    """
    if not isinstance(polynomial, int):
        raise TypeError(f"{name} должен быть целым числом")

    if polynomial < 0:
        raise ValueError(
            f"{name} не может быть отрицательным"
        )

    return polynomial


def gf2_polynomial_degree(polynomial: int) -> int:
    """
    Возвращает степень полинома над GF(2).

    Для нулевого полинома возвращается -1.
    """
    polynomial = validate_binary_polynomial(polynomial)

    if polynomial == 0:
        return -1

    return polynomial.bit_length() - 1


def gf2_polynomial_add(
    left: int,
    right: int,
) -> int:
    """
    Складывает два полинома над GF(2).

    Сложение коэффициентов по модулю 2 — это XOR.
    """
    left = validate_binary_polynomial(left, name="left")
    right = validate_binary_polynomial(right, name="right")

    return left ^ right


def gf2_polynomial_subtract(
    left: int,
    right: int,
) -> int:
    """
    Вычитание совпадает со сложением в GF(2).
    """
    return gf2_polynomial_add(left, right)


def gf2_polynomial_multiply(
    left: int,
    right: int,
) -> int:
    """
    Перемножает полиномы над GF(2).
    """
    left = validate_binary_polynomial(left, name="left")
    right = validate_binary_polynomial(right, name="right")

    result = 0
    multiplier = left
    remaining = right

    while remaining:
        if remaining & 1:
            result ^= multiplier

        remaining >>= 1
        multiplier <<= 1

    return result


def gf2_polynomial_divmod(
    dividend: int,
    divisor: int,
) -> tuple[int, int]:
    """
    Делит один полином на другой над GF(2).

    Возвращает:

        quotient
        remainder
    """
    dividend = validate_binary_polynomial(
        dividend,
        name="dividend",
    )

    divisor = validate_binary_polynomial(
        divisor,
        name="divisor",
    )

    if divisor == 0:
        raise ZeroDivisionError(
            "Деление на нулевой полином невозможно"
        )

    quotient = 0
    remainder = dividend

    divisor_degree = gf2_polynomial_degree(divisor)

    while (
        remainder != 0
        and gf2_polynomial_degree(remainder) >= divisor_degree
    ):
        shift = (
            gf2_polynomial_degree(remainder)
            - divisor_degree
        )

        quotient ^= 1 << shift
        remainder ^= divisor << shift

    return quotient, remainder


def gf2_polynomial_mod(
    dividend: int,
    divisor: int,
) -> int:
    """
    Возвращает остаток от деления полиномов.
    """
    _, remainder = gf2_polynomial_divmod(
        dividend=dividend,
        divisor=divisor,
    )

    return remainder


def gf2_polynomial_quotient(
    dividend: int,
    divisor: int,
) -> int:
    """
    Возвращает частное от деления полиномов.
    """
    quotient, _ = gf2_polynomial_divmod(
        dividend=dividend,
        divisor=divisor,
    )

    return quotient


def gf2_polynomial_gcd(
    left: int,
    right: int,
) -> int:
    """
    Находит наибольший общий делитель полиномов над GF(2).
    """
    left = validate_binary_polynomial(left, name="left")
    right = validate_binary_polynomial(right, name="right")

    while right != 0:
        left, right = (
            right,
            gf2_polynomial_mod(left, right),
        )

    return left


def gf2_polynomial_evaluate(
    polynomial: int,
    value: int,
) -> int:
    """
    Вычисляет значение полинома в точке 0 или 1 над GF(2).
    """
    polynomial = validate_binary_polynomial(polynomial)

    if value not in (0, 1):
        raise ValueError(
            "Для полинома над GF(2) value должен быть 0 или 1"
        )

    result = 0
    current = polynomial

    while current:
        coefficient = current & 1
        result = ((result * value) ^ coefficient) & 1
        current >>= 1

    return result


def coefficients_to_integer(
    coefficients: Iterable[int],
) -> int:
    """
    Преобразует список коэффициентов в целое число.

    Коэффициенты передаются от младшей степени к старшей.

    Например:

        [1, 1, 0, 1]

    соответствует:

        1 + x + x^3
        0b1011
    """
    result = 0

    for degree, coefficient in enumerate(coefficients):
        if coefficient not in (0, 1):
            raise ValueError(
                "Коэффициенты должны содержать только 0 и 1"
            )

        if coefficient == 1:
            result |= 1 << degree

    return result


def integer_to_coefficients(
    polynomial: int,
    min_length: int = 1,
) -> list[int]:
    """
    Преобразует целое число в список коэффициентов.

    Коэффициенты возвращаются от младшей степени к старшей.
    """
    polynomial = validate_binary_polynomial(polynomial)

    if min_length <= 0:
        raise ValueError(
            "min_length должно быть положительным"
        )

    required_length = max(
        min_length,
        gf2_polynomial_degree(polynomial) + 1,
    )

    return [
        (polynomial >> degree) & 1
        for degree in range(required_length)
    ]


def polynomial_to_string(
    polynomial: int,
    variable: str = "x",
) -> str:
    """
    Возвращает читаемую строку полинома.

    Например:

        0b1011 -> x^3 + x + 1
    """
    polynomial = validate_binary_polynomial(polynomial)

    if polynomial == 0:
        return "0"

    terms: list[str] = []

    for degree in range(
        gf2_polynomial_degree(polynomial),
        -1,
        -1,
    ):
        if (polynomial >> degree) & 1 == 0:
            continue

        if degree == 0:
            terms.append("1")
        elif degree == 1:
            terms.append(variable)
        else:
            terms.append(f"{variable}^{degree}")

    return " + ".join(terms)

def gf2_polynomial_reciprocal(
    polynomial: int,
) -> int:
    """
    Строит взаимный, или обратный, полином.

    Для:

        p(x) = p_0 + p_1*x + ... + p_d*x^d

    взаимный полином:

        p*(x) = x^d * p(x^-1)

    То есть коэффициенты записываются в обратном порядке.

    Например:

        x^4 + x + 1
        0b10011

    превращается в:

        x^4 + x^3 + 1
        0b11001
    """
    polynomial = validate_binary_polynomial(polynomial)

    if polynomial == 0:
        raise ValueError(
            "Нельзя построить взаимный полином "
            "для нулевого полинома"
        )

    degree = gf2_polynomial_degree(polynomial)
    reciprocal = 0

    for source_degree in range(degree + 1):
        coefficient = (
            polynomial >> source_degree
        ) & 1

        if coefficient == 0:
            continue

        target_degree = degree - source_degree
        reciprocal |= 1 << target_degree

    return reciprocal