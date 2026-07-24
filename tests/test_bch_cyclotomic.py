import pytest

from bch import (
    build_all_binary_cyclotomic_cosets,
    build_binary_cyclotomic_coset,
    canonicalize_binary_cyclotomic_coset,
)


def test_cyclotomic_coset_modulo_15() -> None:
    coset = build_binary_cyclotomic_coset(
        exponent=1,
        code_length=15,
    )

    assert coset == (1, 2, 4, 8)


def test_same_coset_from_different_exponents() -> None:
    coset_1 = build_binary_cyclotomic_coset(
        exponent=1,
        code_length=15,
    )

    coset_2 = build_binary_cyclotomic_coset(
        exponent=2,
        code_length=15,
    )

    assert canonicalize_binary_cyclotomic_coset(
        coset_1
    ) == canonicalize_binary_cyclotomic_coset(
        coset_2
    )


def test_all_cyclotomic_cosets_modulo_15() -> None:
    cosets = build_all_binary_cyclotomic_cosets(15)

    assert cosets == (
        (0,),
        (1, 2, 4, 8),
        (3, 6, 12, 9),
        (5, 10),
        (7, 14, 13, 11),
    )


def test_cosets_partition_all_exponents() -> None:
    code_length = 15

    cosets = build_all_binary_cyclotomic_cosets(
        code_length
    )

    flattened = [
        exponent
        for coset in cosets
        for exponent in coset
    ]

    assert sorted(flattened) == list(
        range(code_length)
    )

    assert len(flattened) == len(set(flattened))


def test_negative_exponent_is_normalized() -> None:
    positive = build_binary_cyclotomic_coset(
        exponent=14,
        code_length=15,
    )

    negative = build_binary_cyclotomic_coset(
        exponent=-1,
        code_length=15,
    )

    assert positive == negative


def test_even_code_length_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_binary_cyclotomic_coset(
            exponent=1,
            code_length=16,
        )