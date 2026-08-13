from __future__ import annotations

from dataclasses import dataclass

from bch.field import GF2m, create_gf2m


@dataclass(frozen=True)
class GoppaConstruction:
    """
    Параметры конструкции бинарного Goppa-кода Γ(L, g).

    field:
        конечное поле GF(2^m)
    goppa_polynomial:
        коэффициенты полинома g(x) над GF(2^m) в порядке
        от свободного до старшего коэффициента
    support:
        кортеж элементов поля L = (α_1, ..., α_n)
    seed:
        seed для воспроизводимости выбора g(x) и support
    """

    field: GF2m
    goppa_polynomial: tuple[int, ...]
    support: tuple[int, ...]
    seed: int

    @property
    def m(self) -> int:
        return self.field.m

    @property
    def n(self) -> int:
        return len(self.support)

    @property
    def degree(self) -> int:
        return len(self.goppa_polynomial) - 1

    @property
    def distance_lower_bound(self) -> int:
        """
        Теоретическая нижняя граница для square-free binary Goppa:
            d_min >= 2 * deg(g) + 1
        """
        return 2 * self.degree + 1


def evaluate_goppa_polynomial(
    field: GF2m,
    goppa_polynomial: tuple[int, ...],
    element: int,
) -> int:
    """
    Вычисляет g(α) в поле GF(2^m).

    g(x) = sum_i c_i * x^i, где c_i принадлежит GF(2^m).
    """
    result = 0

    for coefficient in reversed(goppa_polynomial):
        result = field.add(
            field.multiply(result, element),
            coefficient,
        )

    return result


def _trim_polynomial(polynomial: tuple[int, ...]) -> tuple[int, ...]:
    last = len(polynomial) - 1
    while last > 0 and polynomial[last] == 0:
        last -= 1
    return polynomial[: last + 1]


def _polynomial_remainder(
    field: GF2m,
    dividend: tuple[int, ...],
    divisor: tuple[int, ...],
) -> tuple[int, ...]:
    divisor = _trim_polynomial(divisor)
    if divisor == (0,):
        raise ZeroDivisionError("Деление на нулевой полином")

    remainder = list(_trim_polynomial(dividend))
    divisor_degree = len(divisor) - 1
    divisor_leading_inverse = field.inverse(divisor[-1])

    while len(remainder) - 1 >= divisor_degree and any(remainder):
        shift = len(remainder) - 1 - divisor_degree
        factor = field.multiply(remainder[-1], divisor_leading_inverse)
        for index, coefficient in enumerate(divisor):
            position = index + shift
            remainder[position] = field.add(
                remainder[position],
                field.multiply(factor, coefficient),
            )
        while len(remainder) > 1 and remainder[-1] == 0:
            remainder.pop()

    return tuple(remainder)


def is_square_free(
    field: GF2m,
    goppa_polynomial: tuple[int, ...],
) -> bool:
    """
    Проверяет, что g(x) не имеет кратных корней в замыкании.

    Проверяет условие gcd(g, g') = 1 над GF(2^m).
    """
    polynomial = _trim_polynomial(goppa_polynomial)
    if len(polynomial) <= 1:
        return False

    derivative = tuple(
        polynomial[index] if index % 2 == 1 else 0
        for index in range(1, len(polynomial))
    )
    derivative = _trim_polynomial(derivative)

    if derivative == (0,):
        return False

    left = polynomial
    right = derivative
    while right != (0,):
        left, right = right, _polynomial_remainder(field, left, right)

    return len(_trim_polynomial(left)) == 1


def build_goppa_construction(
    m: int,
    degree: int,
    seed: int = 42,
    primitive_polynomial: int | None = None,
    support_size: int | None = None,
) -> GoppaConstruction:
    """
    Строит детерминированную конструкцию Goppa-кода.

    Параметры:
        m: степень расширения GF(2^m)
        degree: степень Goppa polynomial t_goppa
        seed: seed для выбора g(x) (используется для воспроизводимости)
        primitive_polynomial: примитивный полином поля (None = default)
        support_size: размер support L (None = все элементы поля)

    Алгоритм:
        1. Создаём поле GF(2^m).
        2. Support L = первые support_size элементов поля
           (0, 1, α, α^2, ...) или все, если support_size=None.
        3. Выбираем монический g(x) над GF(2^m) по seed,
            пока g не станет square-free и g(α) != 0 для всех α ∈ L.
    """
    field = create_gf2m(m, primitive_polynomial)

    # Support: все элементы поля или первые support_size
    if support_size is None:
        support_size = field.size

    if support_size > field.size:
        raise ValueError(
            f"support_size={support_size} больше размера поля {field.size}"
        )

    support = tuple(range(support_size))

    # Детерминированный выбор коэффициентов из GF(2^m).
    rng_state = seed

    max_attempts = 1000
    for attempt in range(max_attempts):
        coefficients: list[int] = []
        for _ in range(degree):
            rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            coefficients.append(rng_state % field.size)
        goppa_polynomial = tuple(coefficients + [1])

        # Проверяем условия
        if not is_square_free(field, goppa_polynomial):
            continue

        has_root_on_support = False
        for element in support:
            if evaluate_goppa_polynomial(field, goppa_polynomial, element) == 0:
                has_root_on_support = True
                break

        if not has_root_on_support:
            return GoppaConstruction(
                field=field,
                goppa_polynomial=goppa_polynomial,
                support=support,
                seed=seed,
            )

    raise RuntimeError(
        f"Не удалось построить Goppa polynomial степени {degree} "
        f"за {max_attempts} попыток (m={m}, seed={seed})"
    )
