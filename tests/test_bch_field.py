import pytest

from bch import GF2m, create_gf2m


def test_gf8_alpha_powers() -> None:
    """
    Проверяем поле GF(2^3) с полиномом:

        x^3 + x + 1
    """
    field = GF2m(
        m=3,
        primitive_polynomial=0b1011,
    )

    expected_powers = [
        1,
        2,
        4,
        3,
        6,
        7,
        5,
    ]

    actual_powers = [
        field.alpha(exponent)
        for exponent in range(field.order)
    ]

    assert actual_powers == expected_powers


def test_gf8_contains_all_nonzero_elements() -> None:
    field = create_gf2m(3)

    elements = {
        field.alpha(exponent)
        for exponent in range(field.order)
    }

    assert elements == set(range(1, field.size))


def test_addition_is_xor() -> None:
    field = create_gf2m(3)

    assert field.add(0b101, 0b011) == 0b110
    assert field.subtract(0b101, 0b011) == 0b110


def test_multiplication() -> None:
    field = create_gf2m(3)

    assert field.multiply(0b011, 0b101) == 0b100


def test_division_reverses_multiplication() -> None:
    field = create_gf2m(3)

    for left in range(1, field.size):
        for right in range(1, field.size):
            product = field.multiply(left, right)

            assert field.divide(product, right) == left


def test_inverse() -> None:
    field = create_gf2m(3)

    for value in range(1, field.size):
        inverse = field.inverse(value)

        assert field.multiply(value, inverse) == 1


def test_power() -> None:
    field = create_gf2m(3)

    assert field.power(2, 0) == 1
    assert field.power(2, 1) == 2
    assert field.power(2, 2) == 4
    assert field.power(2, field.order) == 1


def test_gf64_primitive_element_cycle() -> None:
    """
    Это поле понадобится для BCH длины:

        n = 2^6 - 1 = 63
    """
    field = create_gf2m(6)

    elements = {
        field.alpha(exponent)
        for exponent in range(field.order)
    }

    assert field.size == 64
    assert field.order == 63
    assert len(elements) == 63
    assert 0 not in elements


def test_division_by_zero_raises_error() -> None:
    field = create_gf2m(3)

    with pytest.raises(ZeroDivisionError):
        field.divide(1, 0)


def test_zero_has_no_inverse() -> None:
    field = create_gf2m(3)

    with pytest.raises(ZeroDivisionError):
        field.inverse(0)


def test_invalid_element_raises_error() -> None:
    field = create_gf2m(3)

    with pytest.raises(ValueError):
        field.add(8, 1)