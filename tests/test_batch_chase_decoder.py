import numpy as np

from decode.chase_decoding import chase_decode
from decode.syndrome_decoding import build_syndrome_table
from research.code_factory import build_code_from_config
from research.config import WAVELET_16_8_CONFIG
from research.decoder_wrappers import chase_decode_batch


def test_vectorized_chase_matches_scalar_chase() -> None:
    code = build_code_from_config(WAVELET_16_8_CONFIG)
    rng = np.random.default_rng(20260819)
    messages = rng.integers(0, 2, size=(12, code.k), dtype=np.uint8)
    codewords = (messages @ code.generator_matrix) % 2
    errors = np.zeros_like(codewords)
    errors[np.arange(8), np.arange(8)] = 1
    received_words = codewords ^ errors
    received_symbols = 1.0 - 2.0 * received_words + rng.normal(0.0, 0.15, size=received_words.shape)
    reliability = np.abs(received_symbols)
    table = build_syndrome_table(code.parity_check_matrix, max_error_weight=1)
    batch = chase_decode_batch(
        received_words, received_symbols, reliability,
        code.parity_check_matrix, code.generator_matrix,
        unreliable_positions_count=3, inner_decoder_max_error_weight=1, syndrome_table=table,
    )
    scalar = [
        chase_decode(
            received_word=word, received_symbols=symbols, reliability=rel,
            parity_check_matrix=code.parity_check_matrix, generator_matrix=code.generator_matrix,
            unreliable_positions_count=3, inner_decoder_max_error_weight=1, syndrome_table=table,
        )
        for word, symbols, rel in zip(received_words, received_symbols, reliability)
    ]
    assert np.array_equal(batch.success_flags, np.array([item.success for item in scalar]))
    assert np.array_equal(batch.ambiguous_flags, np.array([item.ambiguous for item in scalar]))
    expected_codewords = np.vstack([item.decoded_codeword if item.decoded_codeword is not None else np.zeros(code.n, dtype=np.uint8) for item in scalar])
    expected_messages = np.vstack([item.decoded_message if item.decoded_message is not None else np.zeros(code.k, dtype=np.uint8) for item in scalar])
    assert np.array_equal(batch.decoded_codewords, expected_codewords)
    assert np.array_equal(batch.decoded_messages, expected_messages)
