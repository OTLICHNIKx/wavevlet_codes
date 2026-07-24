from itertools import combinations

import numpy as np

from research.code_factory import (
    build_code_from_config,
)

from research.config import (
    BCH_15_7_CONFIG,
    BCH_63_45_CONFIG,
    WAVELET_16_8_CONFIG,
)

from research.decoder_wrappers import (
    syndrome_decode_batch,
)


def build_received_words_with_errors(
    codeword: np.ndarray,
    max_error_weight: int,
) -> np.ndarray:
    """
    Строит все варианты слова с ошибками
    веса от 0 до max_error_weight.
    """
    received_words: list[np.ndarray] = []

    for weight in range(
        max_error_weight + 1
    ):
        for positions in combinations(
            range(len(codeword)),
            weight,
        ):
            received = codeword.copy()

            for position in positions:
                received[position] ^= 1

            received_words.append(received)

    return np.asarray(
        received_words,
        dtype=np.uint8,
    )


def test_code_factory_builds_wavelet() -> None:
    code = build_code_from_config(
        WAVELET_16_8_CONFIG
    )

    assert code.n == 16
    assert code.k == 8

    assert code.generator_matrix.shape == (
        8,
        16,
    )

    assert code.parity_check_matrix.shape == (
        8,
        16,
    )


def test_code_factory_builds_bch() -> None:
    code = build_code_from_config(
        BCH_15_7_CONFIG
    )

    assert code.n == 15
    assert code.k == 7

    assert code.generator_matrix.shape == (
        7,
        15,
    )

    assert code.parity_check_matrix.shape == (
        8,
        15,
    )


def test_bch_15_7_syndrome_decoder_corrects_all_errors_up_to_t2() -> None:
    """
    BCH(15,7,>=5) должен гарантированно исправлять
    все ошибки веса не больше 2.
    """
    code = build_code_from_config(
        BCH_15_7_CONFIG
    )

    message = np.asarray(
        [1, 0, 1, 1, 0, 1, 0],
        dtype=np.uint8,
    )

    codeword = code.encode(message)

    received_words = (
        build_received_words_with_errors(
            codeword=codeword,
            max_error_weight=2,
        )
    )

    result = syndrome_decode_batch(
        received_words=received_words,
        parity_check_matrix=(
            code.parity_check_matrix
        ),
        generator_matrix=(
            code.generator_matrix
        ),
        max_error_weight=2,
    )

    expected_messages = np.repeat(
        message[np.newaxis, :],
        repeats=len(received_words),
        axis=0,
    )

    expected_codewords = np.repeat(
        codeword[np.newaxis, :],
        repeats=len(received_words),
        axis=0,
    )

    assert np.all(result.success_flags)

    assert np.array_equal(
        result.decoded_messages,
        expected_messages,
    )

    assert np.array_equal(
        result.decoded_codewords,
        expected_codewords,
    )


def test_bch_63_45_syndrome_decoder_corrects_t3_samples() -> None:
    """
    Проверяет интеграцию большого BCH-кода
    с существующим синдромным декодером.
    """
    code = build_code_from_config(
        BCH_63_45_CONFIG
    )

    rng = np.random.default_rng(12345)

    message = rng.integers(
        low=0,
        high=2,
        size=code.k,
        dtype=np.uint8,
    )

    codeword = code.encode(message)

    received_words: list[np.ndarray] = []

    for weight in (0, 1, 2, 3):
        for _ in range(3):
            received = codeword.copy()

            if weight > 0:
                positions = rng.choice(
                    code.n,
                    size=weight,
                    replace=False,
                )

                received[positions] ^= 1

            received_words.append(received)

    received_matrix = np.asarray(
        received_words,
        dtype=np.uint8,
    )

    result = syndrome_decode_batch(
        received_words=received_matrix,
        parity_check_matrix=(
            code.parity_check_matrix
        ),
        generator_matrix=(
            code.generator_matrix
        ),
        max_error_weight=3,
    )

    expected_messages = np.repeat(
        message[np.newaxis, :],
        repeats=len(received_matrix),
        axis=0,
    )

    expected_codewords = np.repeat(
        codeword[np.newaxis, :],
        repeats=len(received_matrix),
        axis=0,
    )

    assert np.all(result.success_flags)

    assert np.array_equal(
        result.decoded_messages,
        expected_messages,
    )

    assert np.array_equal(
        result.decoded_codewords,
        expected_codewords,
    )