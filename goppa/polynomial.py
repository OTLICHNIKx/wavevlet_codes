"""Операции с полиномами над GF(2) для Goppa-кодов.

Переиспользует bch/polynomial.py, добавляя специфичные для Goppa функции.
"""

from bch.polynomial import (
    gf2_polynomial_add,
    gf2_polynomial_degree,
    gf2_polynomial_divmod,
    gf2_polynomial_gcd,
    gf2_polynomial_multiply,
    validate_binary_polynomial,
)


def is_irreducible_over_gf2(polynomial: int) -> bool:
    """
    Проверяет неприводимость полинома над GF(2).

    Полином степени d неприводим, если:
        1. x^(2^d) ≡ x (mod p(x))
        2. gcd(x^(2^i) - x, p(x)) = 1 для всех i < d

    Для малых степеней (d ≤ 8) используем перебор делителей.
    """
    polynomial = validate_binary_polynomial(polynomial)
    degree = gf2_polynomial_degree(polynomial)

    if degree < 1:
        return False

    if degree == 1:
        return polynomial in (0b10, 0b11)  # x, x+1

    # Проверка делимости на все полиномы степени 1..degree//2
    for divisor_degree in range(1, degree // 2 + 1):
        for divisor in range(
            1 << divisor_degree,
            1 << (divisor_degree + 1),
        ):
            if divisor & 1 == 0:
                continue  # свободный член должен быть 1
            _, remainder = gf2_polynomial_divmod(polynomial, divisor)
            if remainder == 0:
                return False

    return True


def goppa_polynomial_evaluate_gf2m(
    field,
    goppa_polynomial: tuple[int, ...],
    element: int,
) -> int:
    """
    Вычисляет g(α) в GF(2^m).

    g(x) = Σ c_i x^i, где c_i принадлежит GF(2^m).
    """
    from goppa.construction import evaluate_goppa_polynomial

    return evaluate_goppa_polynomial(field, goppa_polynomial, element)


__all__ = [
    "gf2_polynomial_add",
    "gf2_polynomial_degree",
    "gf2_polynomial_divmod",
    "gf2_polynomial_gcd",
    "gf2_polynomial_multiply",
    "validate_binary_polynomial",
    "is_irreducible_over_gf2",
    "goppa_polynomial_evaluate_gf2m",
]
