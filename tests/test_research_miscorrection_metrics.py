import numpy as np

from research.metrics import calculate_batch_metrics


def test_miscorrection_metrics_distinguish_success_from_correctness() -> None:
    original = np.array([[0, 0], [1, 1], [1, 0]], dtype=np.uint8)
    decoded = np.array([[0, 0], [1, 0], [0, 0]], dtype=np.uint8)
    success = np.array([True, True, False])

    metrics = calculate_batch_metrics(
        original_messages=original,
        decoded_messages=decoded,
        success_flags=success,
        ambiguous_flags=np.zeros(3, dtype=bool),
        total_time_sec=0.003,
    )

    assert metrics.miscorrection_count == 1
    assert metrics.miscorrection_rate == 1 / 3
    assert metrics.conditional_miscorrection_rate == 1 / 2
    assert metrics.ber_on_success == 1 / 4
    assert metrics.pessimistic_ber == metrics.ber

def test_conditional_metrics_are_undefined_without_successes() -> None:
    original = np.array(
        [[0, 1], [1, 0]],
        dtype=np.uint8,
    )

    decoded = np.zeros_like(original)

    success = np.array(
        [False, False]
    )

    metrics = calculate_batch_metrics(
        original_messages=original,
        decoded_messages=decoded,
        success_flags=success,
        ambiguous_flags=np.zeros(
            2,
            dtype=bool,
        ),
        total_time_sec=0.001,
    )

    assert metrics.success_count == 0
    assert metrics.successful_decoded_bits == 0
    assert metrics.bit_errors_on_success == 0

    assert metrics.ber_on_success is None

    assert (
        metrics.conditional_miscorrection_rate
        is None
    )
