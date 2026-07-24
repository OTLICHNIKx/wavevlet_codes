import numpy as np

from bch import (
    build_bch_generator_polynomial,
    build_bch_matrices,
    gf2_matrix_rank,
    gf2_polynomial_multiply,
)


def test_hamming_7_4_generator_matrix() -> None:
    construction = build_bch_generator_polynomial(
        m=3,
        designed_distance=3,
    )

    matrices = build_bch_matrices(construction)

    expected = np.asarray(
        [
            [1, 1, 0, 1, 0, 0, 0],
            [0, 1, 1, 0, 1, 0, 0],
            [0, 0, 1, 1, 0, 1, 0],
            [0, 0, 0, 1, 1, 0, 1],
        ],
        dtype=np.uint8,
    )

    assert np.array_equal(
        matrices.generator_matrix,
        expected,
    )


def test_hamming_7_4_parity_check_matrix() -> None:
    construction = build_bch_generator_polynomial(
        m=3,
        designed_distance=3,
    )

    matrices = build_bch_matrices(construction)

    expected = np.asarray(
        [
            [1, 0, 1, 1, 1, 0, 0],
            [0, 1, 0, 1, 1, 1, 0],
            [0, 0, 1, 0, 1, 1, 1],
        ],
        dtype=np.uint8,
    )

    assert np.array_equal(
        matrices.parity_check_matrix,
        expected,
    )


def test_hamming_matrices_are_orthogonal() -> None:
    construction = build_bch_generator_polynomial(
        m=3,
        designed_distance=3,
    )

    matrices = build_bch_matrices(construction)

    product = (
        matrices.generator_matrix
        @ matrices.parity_check_matrix.T
    ) % 2

    assert np.all(product == 0)


def test_check_polynomial_relation() -> None:
    construction = build_bch_generator_polynomial(
        m=4,
        designed_distance=5,
    )

    matrices = build_bch_matrices(construction)

    product = gf2_polynomial_multiply(
        construction.generator_polynomial,
        matrices.check_polynomial,
    )

    expected = (1 << construction.n) | 1

    assert product == expected


def test_bch_15_7_matrix_dimensions() -> None:
    construction = build_bch_generator_polynomial(
        m=4,
        designed_distance=5,
    )

    matrices = build_bch_matrices(construction)

    assert matrices.generator_matrix.shape == (
        7,
        15,
    )

    assert matrices.parity_check_matrix.shape == (
        8,
        15,
    )

    assert gf2_matrix_rank(
        matrices.generator_matrix
    ) == 7

    assert gf2_matrix_rank(
        matrices.parity_check_matrix
    ) == 8

    product = (
        matrices.generator_matrix
        @ matrices.parity_check_matrix.T
    ) % 2

    assert np.all(product == 0)


def test_bch_63_45_matrix_dimensions() -> None:
    construction = build_bch_generator_polynomial(
        m=6,
        designed_distance=7,
    )

    matrices = build_bch_matrices(construction)

    assert matrices.generator_matrix.shape == (
        45,
        63,
    )

    assert matrices.parity_check_matrix.shape == (
        18,
        63,
    )

    assert gf2_matrix_rank(
        matrices.generator_matrix
    ) == 45

    assert gf2_matrix_rank(
        matrices.parity_check_matrix
    ) == 18

    product = (
        matrices.generator_matrix.astype(np.int64)
        @ matrices.parity_check_matrix.astype(
            np.int64
        ).T
    ) % 2

    assert np.all(product == 0)