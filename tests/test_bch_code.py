import numpy as np
import pytest

from bch import BCHCode


def test_create_hamming_bch_code() -> None:
    code = BCHCode.primitive(
        m=3,
        designed_distance=3,
    )

    assert code.n == 7
    assert code.k == 4

    assert code.generator_matrix.shape == (
        4,
        7,
    )

    assert code.parity_check_matrix.shape == (
        3,
        7,
    )

    assert code.guaranteed_error_correction == 1


def test_known_hamming_encoding() -> None:
    code = BCHCode.primitive(
        m=3,
        designed_distance=3,
    )

    message = np.asarray(
        [1, 0, 0, 1],
        dtype=np.uint8,
    )

    codeword = code.encode(message)

    expected = np.asarray(
        [1, 1, 0, 0, 1, 0, 1],
        dtype=np.uint8,
    )

    assert np.array_equal(
        codeword,
        expected,
    )


def test_encoded_word_has_zero_syndrome() -> None:
    code = BCHCode.primitive(
        m=4,
        designed_distance=5,
    )

    message = np.asarray(
        [1, 0, 1, 1, 0, 0, 1],
        dtype=np.uint8,
    )

    codeword = code.encode(message)
    syndrome = code.syndrome(codeword)

    assert np.all(syndrome == 0)
    assert code.is_codeword(codeword)


def test_single_error_has_nonzero_syndrome() -> None:
    code = BCHCode.primitive(
        m=3,
        designed_distance=3,
    )

    message = [1, 0, 0, 1]
    codeword = code.encode(message)

    received = codeword.copy()
    received[2] ^= 1

    syndrome = code.syndrome(received)

    assert np.any(syndrome != 0)
    assert not code.is_codeword(received)


def test_extract_message_round_trip() -> None:
    code = BCHCode.primitive(
        m=4,
        designed_distance=5,
    )

    message = np.asarray(
        [1, 1, 0, 1, 0, 1, 0],
        dtype=np.uint8,
    )

    codeword = code.encode(message)

    restored_message = code.extract_message(
        codeword
    )

    assert np.array_equal(
        restored_message,
        message,
    )


def test_zero_message_encoding() -> None:
    code = BCHCode.primitive(
        m=3,
        designed_distance=3,
    )

    message = np.zeros(
        code.k,
        dtype=np.uint8,
    )

    codeword = code.encode(message)

    assert np.array_equal(
        codeword,
        np.zeros(code.n, dtype=np.uint8),
    )


def test_bch_63_45_code_interface() -> None:
    code = BCHCode.primitive(
        m=6,
        designed_distance=7,
    )

    assert code.n == 63
    assert code.k == 45
    assert code.code_rate == 45 / 63

    assert code.generator_matrix.shape == (
        45,
        63,
    )

    assert code.parity_check_matrix.shape == (
        18,
        63,
    )

    assert code.guaranteed_error_correction == 3


def test_invalid_message_length() -> None:
    code = BCHCode.primitive(
        m=3,
        designed_distance=3,
    )

    with pytest.raises(ValueError):
        code.encode([1, 0, 1])


def test_invalid_message_value() -> None:
    code = BCHCode.primitive(
        m=3,
        designed_distance=3,
    )

    with pytest.raises(ValueError):
        code.encode([1, 0, 2, 1])


def test_extract_message_rejects_corrupted_word() -> None:
    code = BCHCode.primitive(
        m=3,
        designed_distance=3,
    )

    codeword = code.encode(
        [1, 0, 0, 1]
    )

    corrupted = codeword.copy()
    corrupted[0] ^= 1

    with pytest.raises(ValueError):
        code.extract_message(corrupted)