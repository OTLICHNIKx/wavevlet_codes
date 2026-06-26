import numpy as np

from encode_wavelet_codes import encode_wavelet_message
from modulation.modulator import bpsk_modulate
from modulation.demodulator import bpsk_llr, hard_decision_from_llr, reliability_from_llr
from research.decoder_wrappers import (
    chase_decode_batch,
    hard_mld_decode_batch,
    soft_mld_decode_batch,
    syndrome_decode_batch,
)


h = [1, 0]
messages = np.array(
    [
        [1, 0, 1, 1],
        [0, 1, 1, 0],
        [1, 1, 0, 0],
        [0, 0, 1, 1],
        [1, 0, 0, 1],
    ],
    dtype=np.uint8,
)

code, _ = encode_wavelet_message(
    h=h,
    message=messages[0],
)

codewords = (messages @ code.generator_matrix) % 2
symbols = np.asarray([bpsk_modulate(codeword) for codeword in codewords])

rng = np.random.default_rng(155)
sigma = 0.8
received_symbols = symbols + sigma * rng.normal(size=symbols.shape)

llr = bpsk_llr(received_symbols, noise_std=sigma)
received_words = hard_decision_from_llr(llr)
reliability = reliability_from_llr(llr)

parity_check_matrix = code.components["parity_check_matrix"]

results = [
    syndrome_decode_batch(
        received_words=received_words,
        parity_check_matrix=parity_check_matrix,
        generator_matrix=code.generator_matrix,
        max_error_weight=2,
    ),
    hard_mld_decode_batch(
        received_words=received_words,
        generator_matrix=code.generator_matrix,
    ),
    soft_mld_decode_batch(
        received_symbols=received_symbols,
        generator_matrix=code.generator_matrix,
    ),
    chase_decode_batch(
        received_words=received_words,
        received_symbols=received_symbols,
        reliability=reliability,
        parity_check_matrix=parity_check_matrix,
        generator_matrix=code.generator_matrix,
        unreliable_positions_count=4,
        inner_decoder_max_error_weight=2,
    ),
]

print("Исходные сообщения:")
print(messages)

for result in results:
    print()
    print(result.decoder_name)
    print("decoded_messages:")
    print(result.decoded_messages)
    print("success:", result.success_flags.tolist())
    print("ambiguous:", result.ambiguous_flags.tolist())
    print("time:", round(result.total_time_sec, 6))