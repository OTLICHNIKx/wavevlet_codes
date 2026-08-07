import csv
from pathlib import Path

from app.services.results_reader import read_summary, result_schema, zero_adjusted_value


def test_summary_and_zero_floor(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["code_name", "decoder", "ebn0_db", "ber", "total_bits", "message_count"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "code_name": "wavelet",
                "decoder": "chase",
                "ebn0_db": 2.0,
                "ber": 0,
                "total_bits": 320,
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
