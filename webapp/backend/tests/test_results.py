import csv
from pathlib import Path

from app.services.results_reader import read_summary, result_schema, zero_adjusted_value


def test_summary_and_zero_floor(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "code_name",
                "decoder",
                "ebn0_db",
                "ber",
                "pessimistic_ber",
                "ber_on_success",
                "frame_error_rate",
                "failure_rate",
                "miscorrection_rate",
                "conditional_miscorrection_rate",
                "total_bits",
                "successful_decoded_bits",
                "success_count",
                "message_count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "code_name": "wavelet",
                "decoder": "chase",
                "ebn0_db": 2.0,
                "ber": 0,
                "pessimistic_ber": 0,
                "ber_on_success": 0,
                "frame_error_rate": 0,
                "failure_rate": 0,
                "miscorrection_rate": 0,
                "conditional_miscorrection_rate": 0,
                "total_bits": 320,
                "successful_decoded_bits": 256,
                "success_count": 8,
                "message_count": 10,
            }
        )

    columns, rows = read_summary(str(tmp_path))
    schema = result_schema(str(tmp_path))
    assert "ber" in columns
    assert schema["codes"] == ["wavelet"]
    assert "ebn0_db" not in schema["numeric_metrics"]
    assert "message_count" not in schema["numeric_metrics"]
    assert zero_adjusted_value(rows[0], "ber", "hide", 1e-8) is None
    assert zero_adjusted_value(rows[0], "ber", "floor", 1e-8) == 0.5 / 320
    assert zero_adjusted_value(rows[0], "ber", "epsilon", 1e-6) == 1e-6
