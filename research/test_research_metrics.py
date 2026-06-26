import numpy as np

from research.metrics import calculate_batch_metrics


original_messages = np.array(
    [
        [1, 0, 1, 1],
        [0, 1, 1, 0],
        [1, 1, 0, 0],
    ],
    dtype=np.uint8,
)

decoded_messages = np.array(
    [
        [1, 0, 1, 1],
        [0, 1, 0, 0],
        [0, 0, 0, 0],
    ],
    dtype=np.uint8,
)

original_codewords = np.array(
    [
        [1, 0, 0, 1, 1, 1, 1, 1],
        [1, 1, 0, 0, 0, 0, 1, 1],
        [0, 0, 1, 1, 1, 1, 0, 0],
    ],
    dtype=np.uint8,
)

decoded_codewords = np.array(
    [
        [1, 0, 0, 1, 1, 1, 1, 1],
        [1, 1, 0, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    dtype=np.uint8,
)

success_flags = np.array([True, True, False])
ambiguous_flags = np.array([False, True, False])

metrics = calculate_batch_metrics(
    original_messages=original_messages,
    decoded_messages=decoded_messages,
    success_flags=success_flags,
    ambiguous_flags=ambiguous_flags,
    total_time_sec=0.03,
    original_codewords=original_codewords,
    decoded_codewords=decoded_codewords,
)

print(metrics)
print("BER:", metrics.ber)
print("FER:", metrics.frame_error_rate)
print("Codeword error rate:", metrics.codeword_error_rate)
print("Failure rate:", metrics.failure_rate)
print("Ambiguous rate:", metrics.ambiguous_rate)
print("Average time ms:", metrics.avg_time_ms)