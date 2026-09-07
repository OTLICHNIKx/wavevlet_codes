import numpy as np

from decode.syndrome_decoding import build_syndrome_table, syndrome_decode
from research.code_factory import build_code_from_config
from research.config import WAVELET_16_8_CONFIG
from research.decoder_wrappers import syndrome_decode_batch
import research.decoder_wrappers as wrappers


def _received_words() -> tuple[np.ndarray, np.ndarray, object]:
    code = build_code_from_config(WAVELET_16_8_CONFIG)
    rng = np.random.default_rng(20260818)
    messages = rng.integers(0, 2, size=(48, code.k), dtype=np.uint8)
    codewords = (messages @ code.generator_matrix) % 2
    errors = np.zeros_like(codewords)
    errors[np.arange(32), np.arange(32) % code.n] = 1
    return messages, codewords ^ errors, code


def test_batch_syndrome_matches_scalar_decoder_and_recovers_messages() -> None:
    original_messages, received_words, code = _received_words()
    table = build_syndrome_table(code.parity_check_matrix, max_error_weight=1)
    batch = syndrome_decode_batch(
        received_words, code.parity_check_matrix, code.generator_matrix,
        max_error_weight=1, syndrome_table=table,
    )
    scalar = [
        syndrome_decode(
            received_word=word, parity_check_matrix=code.parity_check_matrix,
            generator_matrix=code.generator_matrix, max_error_weight=1,
            syndrome_table=table,
        )
        for word in received_words
    ]
    assert np.array_equal(batch.success_flags, np.array([item.success for item in scalar]))
    assert np.array_equal(batch.decoded_codewords, np.vstack([item.corrected_word for item in scalar]))
    assert np.array_equal(batch.decoded_messages, np.vstack([item.decoded_message for item in scalar]))
    assert np.array_equal(batch.decoded_messages, original_messages)


def test_batch_syndrome_never_calls_scalar_decoder_per_word(monkeypatch) -> None:
    _, received_words, code = _received_words()
    table = build_syndrome_table(code.parity_check_matrix, max_error_weight=1)
    def fail_scalar(*args, **kwargs):
        raise AssertionError("scalar syndrome_decode must not be called by batch path")
    monkeypatch.setattr(wrappers, "syndrome_decode", fail_scalar)
    result = syndrome_decode_batch(
        received_words, code.parity_check_matrix, code.generator_matrix,
        max_error_weight=1, syndrome_table=table,
    )
    assert result.success_flags.all()
