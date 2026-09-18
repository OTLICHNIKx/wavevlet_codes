"""Ручной Монте-Карло эксперимент: 5 семейств кодов x 3 канала x 4 декодера.

Исследование уже реализованных в проекте моделей каналов
(rayleigh_awgn — релеевский i.i.d. по символам + гауссов шум,
rayleigh — квазистатический блоковый, sinusoidal) и всех четырёх
generic декодеров (syndrome, chase, hard_mld, soft_mld) для всех
кодовых семейств проекта в трёх размерностях:

    wavelet, bch_derived, goppa_derived, reed_solomon_binary, ldpc
    x (16,8), (32,16), (64,32)  =>  15 кодов.

Каждый код идёт со своими параметрами декодера из собственного
WAVELET_*/BCH_DERIVED_*/GOPPA_*/REED_SOLOMON_*/LDPC_*_CONFIG; канал и
seed одинаковы для всех семейств одной размерности (common random
numbers).

Существующие encoder/decoder/каналы/эксперименты НЕ изменяются: модуль
только собирает конфигурации через research-машинерию и агрегирует
статистику (mean, sample std, 95% CI по Стьюденту) по комбинациям
код x канал x декодер для каждой точки Eb/N0.

Примечание: для всех кодов (64,32) hard/soft MLD помечаются skipped
(k=32 > max_k_for_mld=16, 2^32 перебор неприменим).

Режимы:
    python research/run_wavelet_channel_decoder_experiment.py --mode quick
    python research/run_wavelet_channel_decoder_experiment.py --mode full

Выход:
    results/wavelet_channel_decoder_statistics.csv
    results/wavelet_channel_decoder_statistics_all_metrics.csv
    results/plots/*.png
    results/experiment_config.json
    results/experiment_log.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from research.config import (
    BCH_DERIVED_16_8_CONFIG,
    BCH_DERIVED_32_16_CONFIG,
    BCH_DERIVED_64_32_CONFIG,
    DecoderResearchConfig,
    GOPPA_16_8_CONFIG,
    GOPPA_32_16_CONFIG,
    GOPPA_64_32_CONFIG,
    LDPC_16_8_CONFIG,
    LDPC_32_16_CONFIG,
    LDPC_64_32_CONFIG,
    REED_SOLOMON_16_8_CONFIG,
    REED_SOLOMON_32_16_CONFIG,
    REED_SOLOMON_64_32_CONFIG,
    ResearchConfig,
    WAVELET_16_8_CONFIG,
    WAVELET_32_16_CONFIG,
    WAVELET_64_32_CONFIG,
)
from research.runner import run_research

RESULTS_DIR = Path("results")
PLOTS_DIR = RESULTS_DIR / "plots"
CSV_PATH = RESULTS_DIR / "wavelet_channel_decoder_statistics.csv"
CONFIG_PATH = RESULTS_DIR / "experiment_config.json"
LOG_PATH = RESULTS_DIR / "experiment_log.txt"

CHANNELS: tuple[str, ...] = ("rayleigh_awgn", "rayleigh", "sinusoidal")
DECODERS: tuple[str, ...] = ("syndrome", "chase", "hard_mld", "soft_mld")

# Все пять семейств проекта в трёх размерностях (15 кодов). Каждый код
# несёт свои t/p из собственного *_CONFIG; канал и seed общие для
# семейств одной размерности (common random numbers). hard/soft MLD для
# всех (64,32) skipped: k=32 > max_k_for_mld=16.
_ALL_CODE_CONFIGS = (
    WAVELET_16_8_CONFIG,
    BCH_DERIVED_16_8_CONFIG,
    GOPPA_16_8_CONFIG,
    REED_SOLOMON_16_8_CONFIG,
    LDPC_16_8_CONFIG,
    WAVELET_32_16_CONFIG,
    BCH_DERIVED_32_16_CONFIG,
    GOPPA_32_16_CONFIG,
    REED_SOLOMON_32_16_CONFIG,
    LDPC_32_16_CONFIG,
    WAVELET_64_32_CONFIG,
    BCH_DERIVED_64_32_CONFIG,
    GOPPA_64_32_CONFIG,
    REED_SOLOMON_64_32_CONFIG,
    LDPC_64_32_CONFIG,
)
CODE_CONFIGS = {config.name: config for config in _ALL_CODE_CONFIGS}
CODES: tuple[str, ...] = tuple(CODE_CONFIGS)

# Метрики, по которым считается Монте-Карло статистика (mean/std/95% CI).
STAT_METRICS: tuple[str, ...] = (
    "ber",
    "frame_error_rate",
    "failure_rate",
    "miscorrection_rate",
    "conditional_miscorrection_rate",
    "ambiguous_rate",
    "average_decoding_time_ms",
)
RATE_METRICS: tuple[str, ...] = STAT_METRICS[:-1]
ALL_METRICS_CSV_NAME = "wavelet_channel_decoder_statistics_all_metrics.csv"

SINUSOIDAL_PARAMS = {
    "mode": "fixed",
    "amplitude": 0.5,
    "frequency": 0.125,
    "phase": 0.0,
}
EBN0_GRID: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

ROBUSTNESS_SEED_COUNTS = (10, 30, 50)


@dataclass(frozen=True)
class ExperimentSettings:
    mode: str = "quick"
    num_seeds: int = 50
    words_per_seed: int = 1000
    ebn0_db_values: tuple[float, ...] = EBN0_GRID
    channels: tuple[str, ...] = CHANNELS
    decoders: tuple[str, ...] = DECODERS
    codes: tuple[str, ...] = CODES

    def seed_list(self) -> list[int]:
        return list(range(self.num_seeds))


def build_experiment_config(
    channel_type: str,
    settings: ExperimentSettings,
    seed: int,
) -> ResearchConfig:
    """
    Один запуск: выбранные коды (по умолчанию 15 = 5 семейств
    размерности), 4 декодера, выбранный канал, свой seed.

    Каждый код идёт со своими t/p из WAVELET_*_CONFIG; общие message/
    noise seed'ы обеспечивают сопоставимость и воспроизводимость.
    """
    code_configs = tuple(CODE_CONFIGS[name] for name in settings.codes)
    decoders = DecoderResearchConfig(
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=2,
        chase_unreliable_positions_count=6,
        run_syndrome=True,
        run_hard_mld=True,
        run_soft_mld=True,
        run_chase=True,
        max_k_for_mld=16,
    )
    channel_params: dict[str, Any] = {}
    if channel_type == "sinusoidal":
        channel_params = dict(SINUSOIDAL_PARAMS)
    return ResearchConfig(
        message_count=settings.words_per_seed,
        message_seed=seed,
        noise_seed=10_000 + seed,
        ebn0_db_values=tuple(settings.ebn0_db_values),
        codes=code_configs,
        decoders=decoders,
        results_dir=str(RESULTS_DIR / "_scratch"),
        channel_type=channel_type,
        channel_params=channel_params,
    )


def student_t_975(df: int) -> float:
    """t_0.975 для двусторонней 95% CI (Cornish-Fisher разложение)."""
    exact = {1: 12.7062, 2: 4.3027, 3: 3.1824}
    if df <= 0:
        return float("nan")
    if df in exact:
        return exact[df]
    z = 1.959_963_984_540_054
    v = float(df)
    return (
        z
        + (z**3 + z) / (4 * v)
        + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * v**2)
        + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * v**3)
    )


def summarize(values: list[float]) -> dict[str, float]:
    count = len(values)
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if count > 1 else 0.0
    half = (
        student_t_975(count - 1) * std / (count ** 0.5)
        if std > 0
        else 0.0
    )
    return {
        "mean": mean,
        "std": std,
        "ci_low": max(0.0, mean - half),
        "ci_high": mean + half,
        "half_width": half,
        "n": count,
    }


class ExperimentLogger:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        self.lines.append(line)
        print(line, flush=True)

    def write(self, path: Path) -> None:
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def collect_runs(
    settings: ExperimentSettings, logger: ExperimentLogger
) -> dict[tuple[str, str, str, float], dict[str, Any]]:
    """
    { (code, channel, decoder, ebn0) -> {"ber": [...], "time_ms": [...]} }
    по всем seed; строки MLD-skipped не учитываются.
    """
    samples: dict[tuple[str, str, str, float], dict[str, list[float]]] = {}
    skipped: dict[str, set[str]] = {}
    total_runs = len(settings.channels) * settings.num_seeds
    run_index = 0
    for channel_type in settings.channels:
        for seed in settings.seed_list():
            run_index += 1
            started = time.perf_counter()
            config = build_experiment_config(channel_type, settings, seed)
            rows = run_research(config)
            for row in rows:
                if row["decoder"] not in settings.decoders:
                    continue
                if row["skipped"]:
                    skipped.setdefault(row["code_name"], set()).add(
                        row["decoder"]
                    )
                    continue
                key = (
                    row["code_name"],
                    channel_type,
                    row["decoder"],
                    float(row["ebn0_db"]),
                )
                bucket = samples.setdefault(
                    key, {"ber": [], "time_ms": [],
                          "metrics": {m: [] for m in STAT_METRICS}}
                )
                bucket["ber"].append(float(row["ber"]))
                bucket["time_ms"].append(float(row["avg_time_ms"]))
                for metric in STAT_METRICS:
                    value = row.get(metric)
                    if value is None or value == "":
                        continue
                    bucket["metrics"][metric].append(float(value))
            logger.log(
                f"run {run_index}/{total_runs} channel={channel_type} "
                f"seed={seed} words={settings.words_per_seed} "
                f"codes={len(settings.codes)} "
                "({:.1f}s)".format(time.perf_counter() - started)
            )
    for code_name, decoders in sorted(skipped.items()):
        logger.log(
            f"skipped: {code_name}: "
            f"{', '.join(sorted(decoders))} (k=32 > max_k_for_mld=16)"
        )
    return samples


def check_reproducibility(settings: ExperimentSettings, logger: ExperimentLogger) -> None:
    """Один и тот же seed/канал при повторном запуске даёт идентичный BER."""
    channel_type = settings.channels[0]
    config = build_experiment_config(channel_type, settings, 0)
    first = {
        (row["code_name"], row["decoder"], row["ebn0_db"]): row["ber"]
        for row in run_research(config)
        if not row["skipped"]
    }
    second = {
        (row["code_name"], row["decoder"], row["ebn0_db"]): row["ber"]
        for row in run_research(config)
        if not row["skipped"]
    }
    identical = first == second
    logger.log(
        "reproducibility check "
        f"(channel={channel_type}, seed=0, {len(first)} результат-строк): "
        f"{'OK' if identical else 'FAIL'}"
    )
    if not identical:
        raise AssertionError("невозпроизводимый результат")


def write_statistics_csv(
    samples: dict[tuple[str, str, str, float], dict[str, Any]],
    settings: ExperimentSettings,
    logger: ExperimentLogger,
) -> list[dict[str, Any]]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    header = [
        "code", "channel", "decoder", "parameter", "mean_BER", "std_BER",
        "ci_low", "ci_high", "seeds", "words", "decode_time",
    ]
    aggregated: list[dict[str, Any]] = []
    for code_name in settings.codes:
        for channel_type in settings.channels:
            for decoder in settings.decoders:
                for ebn0 in settings.ebn0_db_values:
                    bucket = samples.get((code_name, channel_type, decoder, ebn0))
                    if not bucket or not bucket["ber"]:
                        continue
                    stats = summarize(bucket["ber"])
                    aggregated.append(
                        {
                            "code": code_name,
                            "channel": channel_type,
                            "decoder": decoder,
                            "parameter": ebn0,
                            "mean_BER": f"{stats['mean']:.8f}",
                            "std_BER": f"{stats['std']:.8f}",
                            "ci_low": f"{stats['ci_low']:.8f}",
                            "ci_high": f"{stats['ci_high']:.8f}",
                            "seeds": stats["n"],
                            "words": settings.words_per_seed,
                            "decode_time": (
                                f"{statistics.fmean(bucket['time_ms']):.4f}"
                            ),
                        }
                    )
    with CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(aggregated)
    logger.log(f"CSV: {CSV_PATH} ({len(aggregated)} строк)")
    return aggregated


def write_robustness_table(
    samples: dict[tuple[str, str, str, float], dict[str, list[float]]],
    settings: ExperimentSettings,
    logger: ExperimentLogger,
) -> None:
    """CI half-width по префиксам seed (10/30/50 или доступный максимум)."""
    available = sorted({
        len(b["ber"]) for b in samples.values() if b.get("ber")
    })
    checkpoints = [n for n in ROBUSTNESS_SEED_COUNTS if n <= (available[-1] if available else 0)]
    if not checkpoints:
        checkpoints = available[-1:]
    worst_curve = max(
        samples.items(), key=lambda item: len(item[1]["ber"])
    )
    logger.log("статистическая устойчивость (CI half-width, худшая кривая):")
    previous = None
    for count in checkpoints:
        stats = summarize(worst_curve[1]["ber"][:count])
        note = ""
        if previous is not None:
            note = " (сужение x{:.2f})".format(
                previous / stats["half_width"] if stats["half_width"] else float("inf")
            )
        logger.log(
            f"  N={count}: ci_half={stats['half_width']:.6f}{note}"
        )
        previous = stats["half_width"] or previous


def plot_curves(
    samples: dict[tuple[str, str, str, float], dict[str, Any]],
    settings: ExperimentSettings,
    logger: ExperimentLogger,
) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    made = 0
    for code_name in settings.codes:
        for channel_type in settings.channels:
            for decoder in settings.decoders:
                means, lows, highs, xs = [], [], [], []
                for ebn0 in settings.ebn0_db_values:
                    bucket = samples.get(
                        (code_name, channel_type, decoder, float(ebn0))
                    )
                    if not bucket or not bucket["ber"]:
                        continue
                    stats = summarize(bucket["ber"])
                    xs.append(ebn0)
                    means.append(max(stats["mean"], 1e-12))
                    lows.append(max(stats["ci_low"], 1e-12))
                    highs.append(stats["ci_high"])
                if not xs:
                    continue
                figure, axis = plt.subplots(figsize=(6, 4))
                lows = [min(l, m) for l, m in zip(lows, means)]
                highs = [max(h, m) for h, m in zip(highs, means)]
                axis.semilogy(xs, means, marker="o", label="mean BER")
                axis.fill_between(
                    xs, lows, highs, alpha=0.25, label="95% CI"
                )
                axis.errorbar(
                    xs, means,
                    yerr=[
                        [max(m - l, 0.0) for m, l in zip(means, lows)],
                        [max(h - m, 0.0) for h, m in zip(highs, means)],
                    ],
                    fmt="none", ecolor="black", capsize=3,
                )
                axis.set_xlabel("Eb/N0, dB")
                axis.set_ylabel("BER")
                axis.set_title(f"{code_name}: {channel_type} + {decoder}")
                axis.grid(True, which="both", alpha=0.3)
                axis.legend()
                path = (
                    PLOTS_DIR
                    / f"{code_name}_{channel_type}_{decoder}_ber.png"
                )
                figure.savefig(path, dpi=140, bbox_inches="tight")
                plt.close(figure)
                made += 1
    expected = len(settings.codes) * len(settings.channels) * len(settings.decoders)
    logger.log(
        f"графиков построено: {made} (максимум {expected}, "
        "без MLD-кривых для кодов (64,32) — skipped)"
    )


def write_all_metrics_csv(
    samples: dict[tuple[str, str, str, float], dict[str, Any]],
    settings: ExperimentSettings,
    logger: ExperimentLogger,
    path: Path | None = None,
) -> Path:
    """
    Длинный CSV со статистикой по всем метрикам (для веб-отображения):
    code,channel,decoder,parameter,metric,mean,std,ci_low,ci_high,seeds,words.
    """
    target = path if path is not None else RESULTS_DIR / ALL_METRICS_CSV_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "code", "channel", "decoder", "parameter", "metric", "mean", "std",
        "ci_low", "ci_high", "seeds", "words",
    ]
    rows: list[dict[str, Any]] = []
    for code_name in settings.codes:
        for channel_type in settings.channels:
            for decoder in settings.decoders:
                for ebn0 in settings.ebn0_db_values:
                    bucket = samples.get(
                        (code_name, channel_type, decoder, ebn0)
                    )
                    if not bucket:
                        continue
                    for metric in STAT_METRICS:
                        values = bucket["metrics"].get(metric) or []
                        if not values:
                            continue
                        stats = summarize(values)
                        rows.append(
                            {
                                "code": code_name,
                                "channel": channel_type,
                                "decoder": decoder,
                                "parameter": ebn0,
                                "metric": metric,
                                "mean": f"{stats['mean']:.8f}",
                                "std": f"{stats['std']:.8f}",
                                "ci_low": f"{stats['ci_low']:.8f}",
                                "ci_high": f"{stats['ci_high']:.8f}",
                                "seeds": stats["n"],
                                "words": settings.words_per_seed,
                            }
                        )
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    logger.log(f"CSV (все метрики): {target} ({len(rows)} строк)")
    return target


def plot_all_metrics_curves(
    samples: dict[tuple[str, str, str, float], dict[str, Any]],
    settings: ExperimentSettings,
    logger: ExperimentLogger,
) -> None:
    """Усреднённые кривые всех метрик: по графику (code x channel x metric)."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    made = 0
    for code_name in settings.codes:
        for channel_type in settings.channels:
            for metric in STAT_METRICS:
                figure, axis = plt.subplots(figsize=(6.5, 4.5))
                any_line = False
                for decoder in settings.decoders:
                    xs, ys, low, high = [], [], [], []
                    for ebn0 in settings.ebn0_db_values:
                        bucket = samples.get(
                            (code_name, channel_type, decoder, ebn0)
                        )
                        values = (bucket or {}).get("metrics", {}).get(
                            metric
                        ) or []
                        if not values:
                            continue
                        stats = summarize(values)
                        xs.append(ebn0)
                        ys.append(max(stats["mean"], 1e-12))
                        low.append(max(stats["ci_low"], 1e-12))
                        high.append(max(stats["ci_high"], 1e-12))
                    if not xs:
                        continue
                    any_line = True
                    axis.plot(xs, ys, marker="o", label=f"{decoder} mean")
                    axis.fill_between(
                        xs, low, high, alpha=0.15,
                        label=f"{decoder} 95% CI",
                    )
                if not any_line:
                    plt.close(figure)
                    continue
                if metric in RATE_METRICS:
                    axis.set_yscale("log")
                axis.set_xlabel("Eb/N0, dB")
                axis.set_ylabel(metric)
                axis.set_title(f"{code_name}: {channel_type} — {metric}")
                axis.grid(True, which="both", alpha=0.3)
                axis.legend(fontsize=7)
                path = (
                    PLOTS_DIR
                    / f"mc_{code_name}_{channel_type}_{metric}.png"
                )
                figure.savefig(path, dpi=140, bbox_inches="tight")
                plt.close(figure)
                made += 1
    logger.log(f"графиков по всем метрикам: {made}")


def write_experiment_config(settings: ExperimentSettings) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "codes": {
            name: {
                "n": CODE_CONFIGS[name].n,
                "k": CODE_CONFIGS[name].k,
                "syndrome_max_error_weight": CODE_CONFIGS[name].syndrome_max_error_weight,
                "chase_inner_decoder_max_error_weight": CODE_CONFIGS[name].chase_inner_decoder_max_error_weight,
                "chase_unreliable_positions_count": CODE_CONFIGS[name].chase_unreliable_positions_count,
            }
            for name in settings.codes
        },
        "settings": asdict(settings),
        "channels": list(CHANNELS),
        "decoders": list(DECODERS),
        "channel_params": {
            "rayleigh_awgn": "i.i.d. Rayleigh h (E[h^2]=1) + gaussian noise",
            "rayleigh": "quasi-static Rayleigh h (E[h^2]=1) + scaled noise",
            "sinusoidal": SINUSOIDAL_PARAMS,
        },
        "statistics": "mean, sample std (ddof=1), 95% CI Student t (df=N-1)",
        "seed_scheme": "message_seed=seed, noise_seed=10000+seed, seed 0..N-1",
        "combinations": (
            len(settings.codes) * len(CHANNELS) * len(DECODERS)
        ),
        "note_mld": (
            "hard/soft MLD для всех кодов (64,32) skipped: "
            "k=32 > max_k_for_mld=16 (2^32 перебор неприменим)"
        ),
    }
    CONFIG_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--seeds", type=int, default=None)
    parser.add_argument("--words", type=int, default=None)
    args = parser.parse_args()

    if args.mode == "quick":
        settings = ExperimentSettings(
            mode="quick", num_seeds=5, words_per_seed=100
        )
    else:
        settings = ExperimentSettings(mode="full")
    if args.seeds:
        settings = replace(settings, num_seeds=args.seeds)
    if args.words:
        settings = replace(settings, words_per_seed=args.words)

    logger = ExperimentLogger()
    logger.log(
        f"старт: mode={settings.mode} seeds={settings.num_seeds} "
        f"words={settings.words_per_seed} ebn0={settings.ebn0_db_values}"
    )
    logger.log(
        f"коды: {', '.join(settings.codes)}; "
        f"каналы: {', '.join(settings.channels)}; "
        f"декодеры: {', '.join(settings.decoders)}; "
        f"комбинаций код-канал-декодер: "
        f"{len(settings.codes) * len(settings.channels) * len(settings.decoders)}"
    )
    write_experiment_config(settings)
    started = time.perf_counter()

    check_reproducibility(settings, logger)
    samples = collect_runs(settings, logger)
    write_statistics_csv(samples, settings, logger)
    write_all_metrics_csv(samples, settings, logger)
    write_robustness_table(samples, settings, logger)
    plot_curves(samples, settings, logger)
    plot_all_metrics_curves(samples, settings, logger)

    logger.log(f"всего времени: {time.perf_counter() - started:.1f}s")
    logger.write(LOG_PATH)
    print(f"лог: {LOG_PATH}")


if __name__ == "__main__":
    main()
