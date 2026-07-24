import numpy as np

from bch import BCHDerivedCode

from research.code_factory import (
    build_code_from_config,
)

from research.config import (
    BCH_DERIVED_64_32_CONFIG,
)


def test_factory_builds_bch_derived_64_32() -> None:
    code = build_code_from_config(
        BCH_DERIVED_64_32_CONFIG
    )

    assert isinstance(
        code,
        BCHDerivedCode,
    )

    assert code.n == 64
    assert code.k == 32

    assert code.generator_matrix.shape == (
        32,
        64,
    )

    assert code.parity_check_matrix.shape == (
        32,
        64,
    )

    # Консервативная теоретическая гарантия конструкции:
    # d_min >= 11 - 3 = 8, поэтому t = 3.
    assert code.guaranteed_error_correction == 3


def test_factory_bch_derived_matrices_are_orthogonal() -> None:
    code = build_code_from_config(
        BCH_DERIVED_64_32_CONFIG
    )

    product = np.mod(
        code.generator_matrix.astype(np.int64)
        @ code.parity_check_matrix.astype(
            np.int64
        ).T,
        2,
    )

    assert np.all(product == 0)


def test_factory_bch_derived_encoding() -> None:
    code = build_code_from_config(
        BCH_DERIVED_64_32_CONFIG
    )

    rng = np.random.default_rng(12345)

    for _ in range(20):
        message = rng.integers(
            low=0,
            high=2,
            size=32,
            dtype=np.uint8,
        )

        codeword = code.encode(message)

        assert codeword.shape == (64,)
        assert code.is_codeword(codeword)

        restored = code.extract_message(
            codeword
        )

        assert np.array_equal(
            restored,
            message,
        )