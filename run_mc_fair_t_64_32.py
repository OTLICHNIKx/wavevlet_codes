#!/usr/bin/env python3
"""
Монте-Карло «честный t» только для (64,32): 5 семейств × 3 канала ×
4 декодера × 50 сидов × 1000 слов.

Каждый код получает syndrome t и chase p по СВОЕМУ точному d_min
(MITM-перебор), так же как в run_fair_t_64_32.py (bulk 100k):
    wavelet  d=12 -> t=5, p=6
    goppa    d=11 (deg=5, seed=9) -> t=5, p=6
    rs       d=10 -> t=4, p=5
    bch      d=9  -> t=4, p=5
    ldpc     d=9  -> t=4, p=5
Hard/Soft MLD при k=32 пропускаются (k > max_k_for_mld=16), как обычно.

Сетка Eb/N0 расширена до 0..12 dB (18 точек), чтобы увидеть водопад
с CI по сидам (в старом MC 0..6 dB вейвлет/goppa оставались в перегрузе).

Глобальные пресеты *_64_32_CONFIG НЕ изменяются — честные конфиги
собираются через dataclasses.replace и живут только здесь.

Результаты: research_results/mc_fair_t_64_32/
    wavelet_channel_decoder_statistics.csv
    wavelet_channel_decoder_statistics_all_metrics.csv
    plots/*.png
    experiment_config.json
    experiment_log.txt

Запуск:  python run_mc_fair_t_64_32.py
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import research.run_wavelet_channel_decoder_experiment as mc
from research.config import (
    BCH_DERIVED_64_32_CONFIG,
    GOPPA_64_32_CONFIG,
    LDPC_64_32_CONFIG,
    REED_SOLOMON_64_32_CONFIG,
    WAVELET_64_32_CONFIG,
)
from research.runner import run_research

RESULTS_DIR = _ROOT / "research_results" / "mc_fair_t_64_32"
PLOTS_DIR = RESULTS_DIR / "plots"
CSV_PATH = RESULTS_DIR / "wavelet_channel_decoder_statistics.csv"
ALL_METRICS_PATH = RESULTS_DIR / "wavelet_channel_decoder_statistics_all_metrics.csv"
CONFIG_PATH = RESULTS_DIR / "experiment_config.json"
LOG_PATH = RESULTS_DIR / "experiment_log.txt"

CHANNELS = ("rayleigh", "rayleigh_awgn", "sinusoidal")
DECODERS = ("syndrome", "chase", "hard_mld", "soft_mld")
EBN0_18 = tuple(
    [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    + [6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
)
NUM_SEEDS = 50
WORDS_PER_SEED = 1000


def _fair(
    base, name, family_d, t, p, evidence, **goppa
):
    """Код-конфиг 64/32 с честным t/p и точным d_min."""
    return dataclasses.replace(
        base,
        name=name,
        minimum_distance_exact=family_d,
        minimum_distance_lower_bound=family_d,
        minimum_distance_upper_bound=family_d,
        distance_evidence=evidence,
        verified_error_correction_radius=t,
        syndrome_max_error_weight=t,
        chase_inner_decoder_max_error_weight=t,
        chase_unreliable_positions_count=p,
        **goppa,
    )


FAIR_CODES = (
    _fair(
        WAVELET_64_32_CONFIG, "wavelet_64_32_fair", 12, 5, 6,
        "exact d_min=12 by full 2^32 meet-in-the-middle enumeration "
        "(A_12=1824); hole on weights 9-11 (all odd zero, A_10=0)",
    ),
    _fair(
        BCH_DERIVED_64_32_CONFIG, "bch_derived_64_32_fair", 9, 4, 5,
        "exact d_min=9 by full 2^32 meet-in-the-middle enumeration (A_9=1)",
    ),
    _fair(
        GOPPA_64_32_CONFIG, "goppa_derived_64_32_deg5_fair", 11, 5, 6,
        "exact d_min=11 by full 2^32 meet-in-the-middle enumeration "
        "(A_11=549); deg=5 bound 2*5+1=11",
        goppa_degree=5,
        goppa_seed=9,
        goppa_primitive_polynomial=None,
    ),
    _fair(
        REED_SOLOMON_64_32_CONFIG, "reed_solomon_binary_64_32_fair", 10, 4, 5,
        "exact d_min=10 by full 2^32 meet-in-the-middle enumeration (A_10=240)",
    ),
    _fair(
        LDPC_64_32_CONFIG, "ldpc_64_32_fair", 9, 4, 5,
        "exact d_min=9 by full 2^32 meet-in-the-middle enumeration (A_9=54)",
    ),
)
CODE_BY_NAME = {c.name: c for c in FAIR_CODES}


def build_fair_config(channel_type: str, seed: int):
    decoders = mc.DecoderResearchConfig(
        syndrome_max_error_weight=4,
        chase_inner_decoder_max_error_weight=4,
        chase_unreliable_positions_count=5,
        run_syndrome=True,
        run_hard_mld=True,
        run_soft_mld=True,
        run_chase=True,
        max_k_for_mld=16,
    )
    channel_params = {}
    if channel_type == "sinusoidal":
        channel_params = dict(mc.SINUSOIDAL_PARAMS)
    return mc.ResearchConfig(
        message_count=WORDS_PER_SEED,
        message_seed=seed,
        noise_seed=10_000 + seed,
        ebn0_db_values=EBN0_18,
        codes=FAIR_CODES,
        decoders=decoders,
        results_dir=str(RESULTS_DIR / "_scratch"),
        channel_type=channel_type,
        channel_params=channel_params,
    )


def collect(logger) -> dict:
    samples: dict = {}
    skipped: dict[str, set[str]] = {}
    total = len(CHANNELS) * NUM_SEEDS
    run_index = 0
    for channel_type in CHANNELS:
        for seed in range(NUM_SEEDS):
            run_index += 1
            started = time.perf_counter()
            rows = run_research(build_fair_config(channel_type, seed))
            for row in rows:
                if row["decoder"] not in DECODERS:
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
                    key,
                    {
                        "ber": [],
                        "time_ms": [],
                        "metrics": {m: [] for m in mc.STAT_METRICS},
                    },
                )
                bucket["ber"].append(float(row["ber"]))
                bucket["time_ms"].append(float(row["avg_time_ms"]))
                for metric in mc.STAT_METRICS:
                    value = row.get(metric)
                    if value is None or value == "":
                        continue
                    bucket["metrics"][metric].append(float(value))
            logger.log(
                f"run {run_index}/{total} channel={channel_type} "
                f"seed={seed} words={WORDS_PER_SEED} codes=5 "
                "({:.1f}s)".format(time.perf_counter() - started)
            )
    for code_name, decs in sorted(skipped.items()):
        logger.log(
            f"skipped: {code_name}: {', '.join(sorted(decs))} "
            "(k=32 > max_k_for_mld=16)"
        )
    return samples


def write_experiment_config():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "codes": {
            c.name: {
                "n": c.n,
                "k": c.k,
                "family": c.family,
                "minimum_distance_exact": c.minimum_distance_exact,
                "syndrome_max_error_weight": c.syndrome_max_error_weight,
                "chase_inner_decoder_max_error_weight": c.chase_inner_decoder_max_error_weight,
                "chase_unreliable_positions_count": c.chase_unreliable_positions_count,
            }
            for c in FAIR_CODES
        },
        "mode": "full (fair t)",
        "num_seeds": NUM_SEEDS,
        "words_per_seed": WORDS_PER_SEED,
        "ebn0_db_values": list(EBN0_18),
        "channels": list(CHANNELS),
        "decoders": list(DECODERS),
        "note_capacity": (
            "wavelet/goppa t=5 p=6 (d=12/11), rs/bch/ldpc t=4 p=5 "
            "(d=10/9/9) — честный полный t по своему d_min"
        ),
        "note_mld": (
            "hard/soft MLD для всех (64,32) skipped: k=32 > "
            "max_k_for_mld=16"
        ),
        "seed_scheme": "message_seed=seed, noise_seed=10000+seed, seed 0..N-1",
    }
    CONFIG_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def check_reproducibility(logger):
    first = {}
    for r in run_research(build_fair_config("rayleigh_awgn", 0)):
        if not r["skipped"]:
            first[(r["code_name"], r["decoder"], r["ebn0_db"])] = r["ber"]
    second = {}
    for r in run_research(build_fair_config("rayleigh_awgn", 0)):
        if not r["skipped"]:
            second[(r["code_name"], r["decoder"], r["ebn0_db"])] = r["ber"]
    ok = first == second
    logger.log(
        f"reproducibility check (channel=rayleigh_awgn, seed=0, "
        f"{len(first)} строк): {'OK' if ok else 'FAIL'}"
    )
    if not ok:
        raise AssertionError("невозпроизводимый результат")


def main() -> None:
    # Перенаправляем выходные пути модуля mc на наш каталог.
    mc.RESULTS_DIR = RESULTS_DIR
    mc.PLOTS_DIR = PLOTS_DIR
    mc.CSV_PATH = CSV_PATH
    mc.LOG_PATH = LOG_PATH

    logger = mc.ExperimentLogger()
    logger.log(
        f"старт: mode=full-fair-t seeds={NUM_SEEDS} "
        f"words={WORDS_PER_SEED} ebn0={EBN0_18}"
    )
    logger.log(
        f"коды: {', '.join(c.name for c in FAIR_CODES)}; "
        f"каналы: {', '.join(CHANNELS)}; декодеры: {', '.join(DECODERS)}"
    )
    write_experiment_config()
    started = time.perf_counter()

    check_reproducibility(logger)
    samples = collect(logger)

    # settings нужен для агрегации/plots в mc.
    settings = mc.ExperimentSettings(
        mode="full",
        num_seeds=NUM_SEEDS,
        words_per_seed=WORDS_PER_SEED,
        ebn0_db_values=EBN0_18,
        channels=CHANNELS,
        decoders=DECODERS,
        codes=tuple(c.name for c in FAIR_CODES),
    )

    write_statistics_fair(samples, settings, logger)
    mc.write_all_metrics_csv(samples, settings, logger)
    mc.write_robustness_table(samples, settings, logger)
    mc.plot_curves(samples, settings, logger)
    mc.plot_all_metrics_curves(samples, settings, logger)

    logger.log(f"всего времени: {time.perf_counter() - started:.1f}s")
    logger.write(LOG_PATH)
    print(f"лог: {LOG_PATH}")


def write_statistics_fair(samples, settings, logger):
    """Как mc.write_statistics_csv, но на нашем CODE_BY_NAME."""
    import csv
    import statistics

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    header = [
        "code", "channel", "decoder", "parameter", "mean_BER", "std_BER",
        "ci_low", "ci_high", "seeds", "words", "decode_time",
    ]
    aggregated = []
    for code_name in settings.codes:
        for channel_type in settings.channels:
            for decoder in settings.decoders:
                for ebn0 in settings.ebn0_db_values:
                    bucket = samples.get((code_name, channel_type, decoder, ebn0))
                    if not bucket or not bucket["ber"]:
                        continue
                    stats = mc.summarize(bucket["ber"])
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


if __name__ == "__main__":
    main()
