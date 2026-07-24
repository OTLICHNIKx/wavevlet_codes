import numpy as np

from wavelet import (
    WaveletCode,
    build_wavelet_code_for_message,
    encode_wavelet_message,
)


def test_wavelet_package_imports() -> None:
    """
    Проверяет, что публичные импорты нового пакета доступны.
    """
    assert WaveletCode is not None
    assert build_wavelet_code_for_message is not None
    assert encode_wavelet_message is not None


def test_wavelet_encoding_after_move() -> None:
    """
    Проверяет, что перенос файлов не изменил кодирование.
    """
    h = [1, 0]
    message = [1, 0, 1, 1]

    code, codeword = encode_wavelet_message(
        h=h,
        message=message,
    )

    assert code.k == 4
    assert code.n == 8

    assert isinstance(codeword, np.ndarray)
    assert codeword.shape == (8,)

    assert np.all(
        (codeword == 0) | (codeword == 1)
    )


def test_legacy_wavelet_import() -> None:
    """
    Временная проверка обратной совместимости.
    """
    from wavelet_codes import WaveletCode as LegacyWaveletCode

    assert LegacyWaveletCode is WaveletCode


def test_legacy_encoder_import() -> None:
    """
    Временная проверка старого пути импорта кодировщика.
    """
    from encode_wavelet_codes import (
        encode_wavelet_message as legacy_encode,
    )

    h = [1, 0]
    message = [1, 0, 1, 1]

    new_code, new_codeword = encode_wavelet_message(
        h=h,
        message=message,
    )

    old_code, old_codeword = legacy_encode(
        h=h,
        message=message,
    )

    assert np.array_equal(
        new_code.generator_matrix,
        old_code.generator_matrix,
    )

    assert np.array_equal(
        new_codeword,
        old_codeword,
    )
