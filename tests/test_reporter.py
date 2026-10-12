"""Тесты модуля reporter: loader, metrics, analyzer, отчёт."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from reporter.analyzer import analyze
from reporter.loader import (
    load_all,
    load_bulk_summary,
    load_mc_statistics,
    parse_code_name,
)
from reporter.metrics import build_comparisons, ber_gain, snr_intervals
from reporter.report_generator import build_report


BULK_HEADER = [
    "code_name",
    "code_family",
    "n",
    "k",
    "ebn0_db",
    "message_count",
    "decoder",
    "skipped",
    "ber",
    "frame_error_rate",
]


def _write_bulk(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BULK_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _bulk_row(code_name, family, n, k, snr, decoder, ber, fer, skipped=False):
    return {
        "code_name": code_name,
        "code_family": family,
        "n": n,
        "k": k,
        "ebn0_db": snr,
        "message_count": 20000,
        "decoder": decoder,
        "skipped": skipped,
        "ber": ber,
        "frame_error_rate": fer,
    }


def test_parse_code_name() -> None:
    assert parse_code_name("wavelet_64_32_four_family") == ("wavelet", 64, 32)
    assert parse_code_name("bch_derived_16_8_four_family") == ("bch_derived", 16, 8)
    assert parse_code_name("reed_solomon_binary_32_16_four_family") == (
        "reed_solomon_binary",
        32,
        16,
    )
    assert parse_code_name("ldpc_64_32") == ("ldpc", 64, 32)
    assert parse_code_name("mystery") == ("unknown", None, None)


def test_ber_gain_basic() -> None:
    assert ber_gain(1e-5, 5e-5) == pytest.approx(5.0)
    assert ber_gain(1e-5, 1e-5) == pytest.approx(1.0)
    assert ber_gain(0.0, 1e-4) == float("inf")
    with pytest.raises(ValueError):
        ber_gain(0.0, 0.0)


def test_snr_intervals_merges_grid() -> None:
    # Шаг сетки 0.5 разрывается только при пропуске точки.
    assert snr_intervals([3.0, 3.5, 4.0, 4.5]) == [(3.0, 4.5)]
    assert snr_intervals([3.0, 3.5, 4.0, 5.0]) == [(3.0, 4.0), (5.0, 5.0)]
    assert snr_intervals([0.0, 0.5, 5.0]) == [(0.0, 0.5), (5.0, 5.0)]
    assert snr_intervals([]) == []


def test_load_bulk_summary_skips_skipped(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    _write_bulk(
        path,
        [
            _bulk_row("wavelet_16_8", "wavelet", 16, 8, 1.0, "syndrome", 0.01, 0.05),
            _bulk_row(
                "wavelet_16_8", "wavelet", 16, 8, 1.0, "soft_mld", 0.02, 0.06,
                skipped=True,
            ),
        ],
    )
    results = load_bulk_summary(path, channel="awgn")
    assert len(results) == 1
    assert results[0].family_group == "wavelet"
    assert results[0].ber == 0.01
    assert results[0].channel == "awgn"


def test_comparisons_and_gain(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    _write_bulk(
        path,
        [
            _bulk_row("wavelet_16_8", "wavelet", 16, 8, 3.0, "syndrome", 1e-5, 1e-4),
            _bulk_row("bch_derived_16_8", "bch_derived", 16, 8, 3.0, "syndrome", 5e-5, 2e-4),
            _bulk_row("ldpc_16_8", "ldpc", 16, 8, 3.0, "syndrome", 2e-5, 1.5e-4),
        ],
    )
    loaded = load_bulk_summary(path, channel="awgn")
    points = build_comparisons(loaded)
    assert len(points) == 2
    by_competitor = {p.competitor: p for p in points}
    assert by_competitor["bch"].gain == pytest.approx(5.0)
    assert by_competitor["ldpc"].gain == pytest.approx(2.0)
    assert all(p.win for p in points)


def test_analyzer_zones_and_losses(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    rows = []
    # Wavelet выигрывает на SNR 4-4.5, проигрывает на SNR 0-0.5.
    for snr, w_ber, b_ber in [
        (0.0, 0.5, 0.3),
        (0.5, 0.4, 0.25),
        (4.0, 1e-4, 5e-4),
        (4.5, 1e-5, 1e-4),
    ]:
        rows.append(_bulk_row("wavelet_16_8", "wavelet", 16, 8, snr, "syndrome", w_ber, w_ber))
        rows.append(_bulk_row("bch_derived_16_8", "bch_derived", 16, 8, snr, "syndrome", b_ber, b_ber))
    _write_bulk(path, rows)

    loaded = load_all(bulk_root=tmp_path, results_root=tmp_path / "no_mc")
    result = analyze(loaded)

    assert result.total_points == 4
    assert result.win_points == 2
    assert len(result.zones) == 1
    assert result.zones[0].snr_start == 4.0
    assert result.zones[0].snr_end == 4.5
    assert len(result.loss_points) == 2
    # Зоны должны содержать эксперименты.
    assert len(result.zones[0].experiments) == 1


def test_zone_experiments_field(tmp_path: Path) -> None:
    """Проверяет, что zone.experiments заполняется."""
    path = tmp_path / "summary.csv"
    _write_bulk(
        path,
        [
            _bulk_row("wavelet_16_8", "wavelet", 16, 8, 3.0, "syndrome", 1e-5, 1e-4),
            _bulk_row("bch_derived_16_8", "bch_derived", 16, 8, 3.0, "syndrome", 5e-5, 1e-4),
        ],
    )
    loaded = load_all(bulk_root=tmp_path, results_root=tmp_path / "no_mc")
    result = analyze(loaded)
    assert len(result.zones) == 1
    # experiment_name = f"{channel}_{size}" where channel = path.parent.parent.name,
    # size = path.parent.name
    expected_exp = f"{path.parent.parent.name}_{path.parent.name}"
    assert result.zones[0].experiments[0] == expected_exp


def test_load_mc_statistics(tmp_path: Path) -> None:
    path = tmp_path / "wavelet_channel_decoder_statistics.csv"
    header = [
        "code", "channel", "decoder", "parameter",
        "mean_BER", "std_BER", "ci_low", "ci_high", "seeds", "words",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerow({
            "code": "wavelet_32_16", "channel": "rayleigh", "decoder": "syndrome",
            "parameter": 3.0, "mean_BER": 0.01, "std_BER": 0.001,
            "ci_low": 0.009, "ci_high": 0.011, "seeds": 50, "words": 1000,
        })
        writer.writerow({
            "code": "ldpc_32_16", "channel": "rayleigh", "decoder": "syndrome",
            "parameter": 3.0, "mean_BER": 0.02, "std_BER": 0.001,
            "ci_low": 0.019, "ci_high": 0.021, "seeds": 50, "words": 1000,
        })
    results = load_mc_statistics(path)
    assert len(results) == 2
    assert all(r.source == "monte_carlo" for r in results)
    assert results[0].snr == 3.0


def test_mc_confirmation_logic(tmp_path: Path) -> None:
    bulk = tmp_path / "bulk" / "awgn" / "16_8_20k" / "summary.csv"
    _write_bulk(
        bulk,
        [
            _bulk_row("wavelet_16_8", "wavelet", 16, 8, 3.0, "syndrome", 1e-5, 1e-4),
            _bulk_row("bch_derived_16_8", "bch_derived", 16, 8, 3.0, "syndrome", 5e-5, 1e-4),
        ],
    )
    mc = tmp_path / "results" / "mc_16_8_awgn"
    mc.mkdir(parents=True)
    (mc / "wavelet_channel_decoder_statistics.csv").write_text(
        "code,channel,decoder,parameter,mean_BER\n"
        "wavelet_16_8,awgn,syndrome,3.0,1e-5\n"
        "bch_derived_16_8,awgn,syndrome,3.0,5e-5\n",
        encoding="utf-8",
    )

    loaded = load_all(bulk_root=tmp_path / "bulk", results_root=tmp_path / "results")
    result = analyze(loaded)
    assert len(result.mc_confirmed) == 1
    assert len(result.mc_unstable) == 0


def test_report_contains_sections(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    _write_bulk(
        path,
        [
            _bulk_row("wavelet_16_8", "wavelet", 16, 8, 4.0, "syndrome", 1e-5, 1e-4),
            _bulk_row("bch_derived_16_8", "bch_derived", 16, 8, 4.0, "syndrome", 5e-5, 2e-4),
        ],
    )
    loaded = load_all(bulk_root=tmp_path, results_root=tmp_path / "none")
    analysis = analyze(loaded)
    report = build_report(loaded, analysis)

    assert "# Wavelet Code Advantage Report" in report
    assert "## Сводка" in report
    assert "# 1. Лучшие области преимущества Wavelet" in report
    assert "# 2. Сравнение Wavelet против каждого семейства кодов" in report
    assert "# 7. Итоговые выводы" in report


def test_load_all_missing_roots(tmp_path: Path) -> None:
    loaded = load_all(
        bulk_root=tmp_path / "absent",
        results_root=tmp_path / "absent2",
    )
    assert loaded.results == []
    assert loaded.bulk_files == []
    assert loaded.mc_files == []
    assert len(loaded.warnings) == 2


def test_load_all_no_warning_when_mc_found_in_alt_root(tmp_path: Path) -> None:
    """MC-файлы не должны вызывать предупреждение, когда найдены в results_root."""
    bulk = tmp_path / "research_results" / "five_families_channels" / "awgn" / "16_8_20k" / "summary.csv"
    _write_bulk(
        bulk,
        [
            _bulk_row("wavelet_16_8", "wavelet", 16, 8, 3.0, "syndrome", 1e-5, 1e-4),
            _bulk_row("bch_derived_16_8", "bch_derived", 16, 8, 3.0, "syndrome", 5e-5, 1e-4),
        ],
    )
    mc_dir = tmp_path / "research" / "results"
    mc_dir.mkdir(parents=True)
    (mc_dir / "wavelet_channel_decoder_statistics.csv").write_text(
        "code,channel,decoder,parameter,mean_BER\n"
        "wavelet_16_8,awgn,syndrome,3.0,1e-5\n"
        "bch_derived_16_8,awgn,syndrome,3.0,5e-5\n",
        encoding="utf-8",
    )
    # results_root указывает прямо на research/results/
    loaded = load_all(
        bulk_root=tmp_path / "research_results" / "five_families_channels",
        results_root=tmp_path / "research" / "results",
    )
    # MC-файлы найдены → предупреждения о MC быть не должно.
    mc_warnings = [w for w in loaded.warnings if "MC" in w or "Monte Carlo" in w]
    assert len(mc_warnings) == 0
    assert len(loaded.mc_files) == 1
