"""Экспериментальный пресет new_channels_comparison.

5 семейств кодов (32,16) x 3 новых канала (rayleigh, sinusoidal,
rayleigh_awgn) x SNR/EbN0 = 0..5 dB x 100 сообщений = 90 точек
(+ опциональный AWGN-baseline: --baseline).

Результаты:
  research_results/channel_comparison/<channel>/summary.csv  (общий
      формат проекта)
  research_results/channel_comparison/new_channels_comparison.json
      (агрегат: family, channel, SNR, message count, BER, ошибки,
       параметры канала, seed)

Запуск:
    python -m research.run_new_channels_comparison
    python -m research.run_new_channels_comparison --channels rayleigh --baseline
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from research.config import (
    NEW_CHANNELS_AWGN_BASELINE_CONFIG,
    NEW_CHANNELS_COMPARISON,
    NEW_CHANNELS_SINUSOIDAL_PARAMS,
)
from research.runner import run_research

from channel import CHANNEL_TYPES, resolve_channel_params

OUTPUT_ROOT = Path("research_results") / "channel_comparison"
AGGREGATE_PATH = OUTPUT_ROOT / "new_channels_comparison.json"

PARAM_FIELDS = (
    "bch_m", "bch_designed_distance", "bch_shortening_count",
    "bch_puncture_count", "bch_puncture_coordinates",
    "goppa_m", "goppa_degree", "goppa_seed",
    "reed_solomon_symbol_n", "reed_solomon_symbol_k",
    "reed_solomon_evaluation_points", "reed_solomon_column_multipliers",
    "h", "shift",
)


def code_parameters(row: dict) -> dict:
    return {
        key: row.get(key)
        for key in ("h", "shift", "bch_m", "goppa_m", "goppa_seed",
                    "reed_solomon_symbol_k")
        if row.get(key) not in (None, "")
    }


def run_channel(channel_type: str, config, baseline: bool) -> list[dict]:
    print(f"\n===== канал: {channel_type} "
          f"({'baseline' if baseline else 'new'}) =====")
    rows = run_research(config)
    out_rows: list[dict] = []
    params = resolve_channel_params(
        channel_type,
        dict(getattr(config, "channel_params", {}) or {}),
    )
    for row in rows:
        if row["skipped"]:
            continue
        out_rows.append(
            {
                "code_family": row["code_family"],
                "code_name": row["code_name"],
                "channel_type": channel_type,
                "is_baseline": baseline,
                "snr_db": row["ebn0_db"],
                "message_count": row["message_count"],
                "n": row["n"],
                "k": row["k"],
                "decoder": row["decoder"],
                "ber": row["ber"],
                "frame_error_rate": row["frame_error_rate"],
                "failure_rate": row["failure_rate"],
                "bit_errors": row["bit_errors"],
                "total_bits": row["total_bits"],
                "frame_errors": row["frame_errors"],
                "channel_params": params,
                "message_seed": config.message_seed,
                "noise_seed": config.noise_seed,
                "minimum_distance_exact": row.get("minimum_distance_exact"),
                "minimum_distance_lower_bound": row.get("minimum_distance_lower_bound"),
                "minimum_distance_upper_bound": row.get("minimum_distance_upper_bound"),
            }
        )
    return out_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--channels",
        nargs="+",
        choices=[c for c in CHANNEL_TYPES if c != "awgn"],
        default=None,
    )
    parser.add_argument("--baseline", action="store_true",
                        help="добавить AWGN-baseline точки")
    args = parser.parse_args()

    channels = args.channels or list(NEW_CHANNELS_COMPARISON)
    all_rows: list[dict] = []
    for channel_type in channels:
        all_rows.extend(
            run_channel(
                channel_type, NEW_CHANNELS_COMPARISON[channel_type], False
            )
        )
    if args.baseline:
        all_rows.extend(
            run_channel("awgn", NEW_CHANNELS_AWGN_BASELINE_CONFIG, True)
        )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "preset": "new_channels_comparison",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "design": {
            "families": sorted({r["code_family"] for r in all_rows}),
            "size": "(32,16)",
            "channels": channels,
            "baseline_awgn": args.baseline,
            "snr_db": list(
                getattr(
                    NEW_CHANNELS_AWGN_BASELINE_CONFIG, "ebn0_db_values"
                )
            ),
            "message_count": 100,
            "decoders": ["syndrome", "chase", "hard_mld", "soft_mld"],
            "sinusoidal_default_params": NEW_CHANNELS_SINUSOIDAL_PARAMS,
            "rayleigh_model": (
                "rayleigh: quasi-static blockwise unit-power Rayleigh "
                "fading + scaled base noise; rayleigh_awgn: i.i.d. "
                "per-symbol Rayleigh + AWGN; received=h*x+noise"
            ),
        },
        "points_expected_new_channels": len(channels) * 5 * 6 * 4,
        "results": all_rows,
    }
    AGGREGATE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nсохранено: {AGGREGATE_PATH} ({len(all_rows)} записей)")


if __name__ == "__main__":
    main()
