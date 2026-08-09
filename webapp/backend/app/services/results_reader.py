"""Безопасное чтение summary.csv и построение набора для Plotly."""

import csv
import math
from pathlib import Path
from typing import Any

from app.core.security import resolve_results_dir


NON_METRIC_NUMERIC_COLUMNS = {
    "n",
    "k",
    "code_rate",
    "bch_m",
    "bch_designed_distance",
    "bch_first_root",
    "bch_primitive_polynomial",
    "bch_shortening_count",
    "bch_puncture_count",
    "expected_min_distance",
    "syndrome_t",
    "chase_inner_t",
    "chase_p",
    "ebn0_db",
    "sigma",
    "message_count",
    "skipped",
    "bit_errors",
    "total_bits",
    "success_count",
    "successful_decoded_bits",
    "bit_errors_on_success",
    "frame_errors",
    "codeword_errors",
    "failure_count",
    "ambiguous_count",
    "miscorrection_count",
    "syndrome_table_build_time_sec",
    "syndrome_table_pattern_count",
    "syndrome_table_entry_count",
    "syndrome_table_collision_count",
    "syndrome_table_memory_bytes",
    "total_time_sec",
}

PREFERRED_METRICS = [
    "frame_error_rate",
    "ber",
    "pessimistic_ber",
    "ber_on_success",
    "failure_rate",
    "miscorrection_rate",
    "conditional_miscorrection_rate",
    "average_decoding_time_ms",
]


def _convert(value: str) -> Any:
    stripped = value.strip()
    if stripped == "":
        return None
    if stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    try:
        number = float(stripped)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def read_summary(results_dir: str) -> tuple[list[str], list[dict[str, Any]]]:
    path = resolve_results_dir(results_dir) / "summary.csv"
    if not path.is_file():
        raise FileNotFoundError("summary.csv не найден")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = [{key: _convert(value) for key, value in row.items()} for row in reader]
    return columns, rows


def result_schema(results_dir: str) -> dict[str, Any]:
    columns, rows = read_summary(results_dir)
    discovered = [
        column
        for column in columns
        if column not in NON_METRIC_NUMERIC_COLUMNS
        and any(isinstance(row.get(column), (int, float)) for row in rows)
    ]
    numeric = [metric for metric in PREFERRED_METRICS if metric in discovered]
    numeric.extend(sorted(set(discovered) - set(numeric)))
    if "average_decoding_time_ms" in numeric and "avg_time_ms" in numeric:
        numeric.remove("avg_time_ms")
    return {
        "columns": columns,
        "numeric_metrics": numeric,
        "codes": sorted({str(row["code_name"]) for row in rows}),
        "decoders": sorted({str(row["decoder"]) for row in rows}),
        "ebn0_db_values": sorted({float(row["ebn0_db"]) for row in rows}),
        "row_count": len(rows),
    }


def zero_adjusted_value(
    row: dict[str, Any], metric: str, mode: str, epsilon: float
) -> float | None:
    value = row.get(metric)
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    if value != 0:
        return float(value)
    if mode == "hide":
        return None
    if mode == "epsilon":
        return epsilon
    if mode == "floor":
        denominator_by_metric = {
            "ber": "total_bits",
            "pessimistic_ber": "total_bits",
            "ber_on_success": "successful_decoded_bits",
            "frame_error_rate": "message_count",
            "failure_rate": "message_count",
            "miscorrection_rate": "message_count",
            "conditional_miscorrection_rate": "success_count",
        }
        denominator_column = denominator_by_metric.get(metric)
        if denominator_column is None:
            return None
        denominator = row.get(denominator_column)
        if isinstance(denominator, (int, float)) and denominator > 0:
            return 0.5 / float(denominator)
    return None