import pytest

from bch import (
    build_bch_generator_polynomial,
    build_binary_cyclotomic_coset,
    build_minimal_polynomial,
    create_gf2m,
    evaluate_binary_polynomial_in_field,
    gf2_polynomial_degree,
    gf2_polynomial_mod,
)


def test_hamming_7_4_generator_polynomial() -> None:
    """
    Примитивный BCH-код:

        BCH(7, 4, 3)

    совпадает с циклическим кодом Хэмминга.
    """
    result = build_bch_generator_polynomial(
        m=3,
        designed_distance=3,
    )

    assert result.n == 7
    assert result.k == 4

    assert result.generator_polynomial == 0b1011
    assert result.generator_degree == 3

    assert result.guaranteed_error_correction == 1


def test_bch_15_11_3_generator_polynomial() -> None:
    result = build_bch_generator_polynomial(
        m=4,
        designed_distance=3,
    )

    assert result.n == 15
    assert result.k == 11

    # x^4 + x + 1
    assert result.generator_polynomial == 0b10011


def test_bch_15_7_5_generator_polynomial() -> None:
    """
    Для BCH(15, 7, 5):

        g(x) = x^8 + x^7 + x^6 + x^4 + 1
    """
    result = build_bch_generator_polynomial(
        m=4,
        designed_distance=5,
    )

    assert result.n == 15
    assert result.k == 7

    assert result.generator_polynomial == 0b111010001
    assert result.generator_degree == 8

    assert result.guaranteed_error_correction == 2

    assert result.root_exponents == (
        1,
        2,
        3,
        4,
    )


def test_bch_63_45_7_parameters() -> None:
    """
    Первый код, близкий к длине исследуемого
    вейвлет-кода (64, 32).

    Примитивный узкий BCH-код:

        BCH(63, 45, >=7)

    гарантированно исправляет 3 ошибки.
    """
    result = build_bch_generator_polynomial(
        m=6,
        designed_distance=7,
    )

    assert result.n == 63
    assert result.k == 45
    assert result.generator_degree == 18

    assert result.guaranteed_error_correction == 3


def test_minimal_polynomial_for_first_coset() -> None:
    field = create_gf2m(4)

    coset = build_binary_cyclotomic_coset(
        exponent=1,
        code_length=field.order,
    )

    minimal_polynomial = build_minimal_polynomial(
        cyclotomic_coset=coset,
        field=field,
    )

    # Для выбранного примитивного элемента:
    #
    # M_1(x) = x^4 + x + 1
    assert minimal_polynomial == 0b10011


def test_generator_has_all_required_roots() -> None:
    result = build_bch_generator_polynomial(
        m=4,
        designed_distance=5,
    )

    field = create_gf2m(
        m=result.m,
        primitive_polynomial=(
            result.primitive_polynomial
        ),
    )

    for exponent in result.root_exponents:
        root = field.alpha(exponent)

        value = evaluate_binary_polynomial_in_field(
            polynomial=result.generator_polynomial,
            value=root,
            field=field,
        )

        assert value == 0


def test_generator_divides_x_n_plus_one() -> None:
    result = build_bch_generator_polynomial(
        m=4,
        designed_distance=5,
    )

    x_n_plus_one = (1 << result.n) | 1

    remainder = gf2_polynomial_mod(
        dividend=x_n_plus_one,
        divisor=result.generator_polynomial,
    )

    assert remainder == 0


def test_generator_dimension_relation() -> None:
    result = build_bch_generator_polynomial(
        m=6,
        designed_distance=7,
    )

    assert result.k == (
        result.n
        - gf2_polynomial_degree(
            result.generator_polynomial
        )
    )


def test_invalid_designed_distance() -> None:
    with pytest.raises(ValueError):
        build_bch_generator_polynomial(
            m=4,
            designed_distance=1,
        )


def test_too_large_designed_distance() -> None:
    with pytest.raises(ValueError):
        build_bch_generator_polynomial(
            m=3,
            designed_distance=8,
        )