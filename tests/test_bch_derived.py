import numpy as np
import pytest

from bch.derived import (
    BCHDerivedCode,
    build_systematic_generator_matrix,
)

from bch.matrices import (
    gf2_matrix_rank,
)


@pytest.fixture(scope="module")
def derived_code() -> BCHDerivedCode:
    """
    Родительский код:

        BCH [127,92,d >= 11]

    Производный код:

        [127,92]
        -> shortening 60
        -> [67,32]
        -> puncturing 3
        -> [64,32]
    """
    return BCHDerivedCode.from_primitive_parent(
        m=7,
        designed_distance=11,
        shortening_count=60,
        puncture_count=3,
        name="bch_derived_64_32",
    )


def test_parent_bch_parameters(
    derived_code: BCHDerivedCode,
) -> None:
    assert derived_code.parent_code.n == 127
    assert derived_code.parent_code.k == 92

    assert (
        derived_code
        .parent_code
        .designed_distance
    ) == 11


def test_parent_generator_can_be_systematic(
    derived_code: BCHDerivedCode,
) -> None:
    result = build_systematic_generator_matrix(
        derived_code.parent_code.generator_matrix
    )

    generator = result.generator_matrix
    k, n = generator.shape

    assert (k, n) == (92, 127)

    assert np.array_equal(
        generator[:, :k],
        np.eye(k, dtype=np.uint8),
    )

    assert gf2_matrix_rank(generator) == 92


def test_derived_code_parameters(
    derived_code: BCHDerivedCode,
) -> None:
    assert derived_code.n == 64
    assert derived_code.k == 32

    assert derived_code.code_rate == 0.5

    assert (
        derived_code.minimum_distance_lower_bound
        == 8
    )

    assert (
        derived_code.guaranteed_error_correction
        == 3
    )


def test_derived_matrix_dimensions(
    derived_code: BCHDerivedCode,
) -> None:
    assert derived_code.generator_matrix.shape == (
        32,
        64,
    )

    assert (
        derived_code.parity_check_matrix.shape
        == (32, 64)
    )


def test_derived_generator_is_systematic(
    derived_code: BCHDerivedCode,
) -> None:
    identity = np.eye(
        32,
        dtype=np.uint8,
    )

    assert np.array_equal(
        derived_code.generator_matrix[:, :32],
        identity,
    )


def test_derived_matrices_have_full_rank(
    derived_code: BCHDerivedCode,
) -> None:
    assert gf2_matrix_rank(
        derived_code.generator_matrix
    ) == 32

    assert gf2_matrix_rank(
        derived_code.parity_check_matrix
    ) == 32


def test_derived_matrices_are_orthogonal(
    derived_code: BCHDerivedCode,
) -> None:
    product = np.mod(
        derived_code.generator_matrix.astype(
            np.int64
        )
        @ derived_code.parity_check_matrix.astype(
            np.int64
        ).T,
        2,
    )

    assert np.all(product == 0)


def test_coordinate_accounting(
    derived_code: BCHDerivedCode,
) -> None:
    assert len(
        derived_code.shortened_parent_coordinates
    ) == 60

    assert len(
        derived_code.punctured_parent_coordinates
    ) == 3

    assert len(
        derived_code.remaining_parent_coordinates
    ) == 64

    all_coordinates = (
        derived_code.shortened_parent_coordinates
        + derived_code.punctured_parent_coordinates
        + derived_code.remaining_parent_coordinates
    )

    assert sorted(all_coordinates) == list(
        range(127)
    )

    assert len(set(all_coordinates)) == 127


def test_encode_has_zero_syndrome(
    derived_code: BCHDerivedCode,
) -> None:
    rng = np.random.default_rng(12345)

    message = rng.integers(
        low=0,
        high=2,
        size=derived_code.k,
        dtype=np.uint8,
    )

    codeword = derived_code.encode(message)

    assert codeword.shape == (64,)
    assert derived_code.is_codeword(codeword)

    assert np.all(
        derived_code.syndrome(codeword) == 0
    )


def test_encode_extract_round_trip(
    derived_code: BCHDerivedCode,
) -> None:
    rng = np.random.default_rng(54321)

    for _ in range(20):
        message = rng.integers(
            low=0,
            high=2,
            size=derived_code.k,
            dtype=np.uint8,
        )

        codeword = derived_code.encode(message)

        restored_message = (
            derived_code.extract_message(
                codeword
            )
        )

        assert np.array_equal(
            restored_message,
            message,
        )


def test_single_error_has_nonzero_syndrome(
    derived_code: BCHDerivedCode,
) -> None:
    message = np.zeros(
        derived_code.k,
        dtype=np.uint8,
    )

    codeword = derived_code.encode(message)

    for position in range(derived_code.n):
        received = codeword.copy()
        received[position] ^= 1

        assert np.any(
            derived_code.syndrome(received)
            != 0
        )


def test_invalid_message_length(
    derived_code: BCHDerivedCode,
) -> None:
    with pytest.raises(ValueError):
        derived_code.encode(
            [0] * 31
        )