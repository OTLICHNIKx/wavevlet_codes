import csv
from pathlib import Path

from research.run_wavelet_channel_decoder_experiment import (
    CODE_CONFIGS,
    STAT_METRICS,
    ExperimentSettings,
    student_t_975,
    summarize,
    write_all_metrics_csv,
)


def make_samples():
    metrics = {
        metric: [0.10, 0.12, 0.08, 0.11, 0.09] for metric in STAT_METRICS
    }
    return {
        ("wavelet_16_8", "rayleigh_awgn", "syndrome", 0.0): {
            "ber": metrics["ber"],
            "time_ms": [1.0] * 5,
            "metrics": metrics,
        },
    }


def test_default_codes_cover_all_families_and_sizes():
    import re

    names = ExperimentSettings().codes
    assert len(names) == 15
    families = {re.sub(r"_\d+_\d+$", "", name) for name in names}
    assert families == {
        "wavelet", "bch_derived", "goppa_derived",
        "reed_solomon_binary", "ldpc",
    }
    sizes = {re.search(r"_(\d+_\d+)$", name).group(1) for name in names}
    assert sizes == {"16_8", "32_16", "64_32"}
    assert all(name in CODE_CONFIGS for name in names)


def test_student_t_known_values():
    assert abs(student_t_975(4) - 2.776) < 0.01
    assert abs(student_t_975(9) - 2.262) < 0.01
    assert abs(student_t_975(49) - 2.009) < 0.01


def test_summarize_ci_contains_mean():
    stats = summarize([0.10, 0.12, 0.08, 0.11, 0.09])
    assert stats["ci_low"] < stats["mean"] < stats["ci_high"]
    assert stats["n"] == 5


def test_write_all_metrics_csv(tmp_path: Path):
    settings = ExperimentSettings(num_seeds=5, words_per_seed=100)
    path = write_all_metrics_csv(
        make_samples(),
        settings,
        _SilentLogger(),
        path=tmp_path / "unit_wavelet_channel_decoder_statistics_all_metrics.csv",
    )
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == len(STAT_METRICS)
    assert {r["metric"] for r in rows} == set(STAT_METRICS)
    ber_row = [r for r in rows if r["metric"] == "ber"][0]
    assert ber_row["code"] == "wavelet_16_8"
    assert float(ber_row["mean"]) > 0
    assert float(ber_row["ci_low"]) <= float(ber_row["mean"]) <= float(ber_row["ci_high"])


class _SilentLogger:
    def log(self, message: str) -> None:
        return
