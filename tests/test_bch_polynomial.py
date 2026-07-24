import pytest

from bch import (
    coefficients_to_integer,
    gf2_polynomial_add,
    gf2_polynomial_degree,
    gf2_polynomial_divmod,
    gf2_polynomial_gcd,
    gf2_polynomial_multiply,
    integer_to_coefficients,
    polynomial_to_string,
)


def test_polynomial_degree() -> None:
    assert gf2_polynomial_degree(0) == -1
    assert gf2_polynomial_degree(1) == 0
    assert gf2_polynomial_degree(0b1011) == 3


def test_polynomial_addition() -> None:
    left = 0b1011
    right = 0b0110

    assert gf2_polynomial_add(left, right) == 0b1101


def test_polynomial_multiplication() -> None:
    """
    (x + 1)(x^2 + x + 1) = x^3 + 1
    """
    left = 0b11
    right = 0b111

    assert gf2_polynomial_multiply(left, right) == 0b1001


def test_polynomial_division_without_remainder() -> None:
    """
    (x^3 + 1) / (x + 1) = x^2 + x + 1
    """
    dividend = 0b1001
    divisor = 0b11

    quotient, remainder = gf2_polynomial_divmod(
        dividend,
        divisor,
    )

    assert quotient == 0b111
    assert remainder == 0


def test_polynomial_division_with_remainder() -> None:
    dividend = 0b1011
    divisor = 0b111

    quotient, remainder = gf2_polynomial_divmod(
        dividend,
        divisor,
    )

    reconstructed = (
        gf2_polynomial_multiply(quotient, divisor)
        ^ remainder
    )

    assert reconstructed == dividend
    assert gf2_polynomial_degree(remainder) < (
        gf2_polynomial_degree(divisor)
    )


def test_polynomial_gcd() -> None:
    """
    gcd(x^3 + 1, x^2 + 1) = x + 1
    """
    assert gf2_polynomial_gcd(
        0b1001,
        0b101,
    ) == 0b11


def test_coefficients_conversion() -> None:
    coefficients = [1, 1, 0, 1]

    polynomial = coefficients_to_integer(coefficients)

    assert polynomial == 0b1011
    assert integer_to_coefficients(polynomial) == coefficients


def test_polynomial_string() -> None:
    assert polynomial_to_string(0) == "0"
    assert polynomial_to_string(1) == "1"
    assert polynomial_to_string(0b1011) == "x^3 + x + 1"


def test_division_by_zero_polynomial() -> None:
    with pytest.raises(ZeroDivisionError):
        gf2_polynomial_divmod(0b1011, 0)