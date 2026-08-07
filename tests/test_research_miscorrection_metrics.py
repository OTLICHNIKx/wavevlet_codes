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
