"""Эксперимент realistic_sinusoidal_channel_test.

5 семейств (32,16) x реалистичная синусоидальная интерференция
x SNR 0..5 dB x 100 сообщений x все 4 декодера (раздельная
статистика по decoder).

Результат: research_results/channel_comparison/realistic_sinusoidal_results.json
(+ summary.csv общего формата проекта в results_dir конфига).

Запуск:
    python -m research.run_realistic_sinusoidal_test
"""

from __future__ import annotations

import json
from pathlib import Path

from research.config import (
    FIVE_FAMILIES_20K_32_16,
    REALISTIC_SINUSOIDAL_TEST_CONFIG,
)
from research.dataset import make_code_seed
from research.runner import run_research

from channel import realized_sinusoidal_parameters

OUTPUT_PATH = (
    Path("research_results") / "channel_comparison" / "realistic_sinusoidal_results.json"
)


def main() -> None:
    config = REALISTIC_SINUSOIDAL_TEST_CONFIG
    params = config.channel_params
    rows = run_research(config)

    sample_code = config.codes[0]
    code_noise_seed = make_code_seed(
        config.noise_seed, sample_code, salt=1_000_000
    )
    channel_seed = code_noise_seed + 2_000_000
    realized = realized_sinusoidal_parameters(
        channel_seed,
        num_interferers=int(params["num_interferers"]),
        amplitude_distribution=str(params["amplitude_distribution"]),
        amplitude_range=tuple(params["amplitude_range"]),
        frequency_range=tuple(params["frequency_range"]),
    )

    results: list[dict] = []
    for row in rows:
        if row["skipped"]:
            entry = {
                "code_family": row["code_family"],
                "code_name": row["code_name"],
                "decoder": row["decoder"],
                "channel": config.channel_type,
                "snr": row["ebn0_db"],
                "seed": {
                    "message_seed": config.message_seed,
                    "noise_seed": config.noise_seed,
                    "channel_seed": channel_seed,
                },
                "message_count": row["message_count"],
                "ber": None,
                "errors": None,
                "skipped": True,
                "skip_reason": row["skip_reason"],
                "channel_parameters": realized,
            }
        else:
            entry = {
                "code_family": row["code_family"],
                "code_name": row["code_name"],
                "decoder": row["decoder"],
                "channel": config.channel_type,
                "snr": row["ebn0_db"],
                "seed": {
                    "message_seed": config.message_seed,
                    "noise_seed": config.noise_seed,
                    "channel_seed": channel_seed,
                },
                "message_count": row["message_count"],
                "ber": row["ber"],
                "errors": row["bit_errors"],
                "total_bits": row["total_bits"],
                "frame_errors": row["frame_errors"],
                "failure_rate": row["failure_rate"],
                "skipped": False,
                "channel_parameters": realized,
            }
        results.append(entry)

    payload = {
        "preset": "realistic_sinusoidal_channel_test",
        "channel_model": (
            "received = signal + sum_k Ai(t)*sin(2*pi*fi(t)*t + phase_i) "
            "+ gaussian_noise; mode=realistic, drift="
            + str(params.get("drift"))
        ),
        "request_channel_parameters": dict(params),
        "realized_interference_parameters": realized,
        "design": {
            "families": sorted({r["code_family"] for r in results}),
            "size": "(32,16)",
            "decoders": sorted({r["decoder"] for r in results}),
            "snr_db": list(config.ebn0_db_values),
            "message_count": config.message_count,
            "points": len(
                {(r["code_family"], r["decoder"], r["snr"]) for r in results}
            ),
        },
        "results": results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"сохранено: {OUTPUT_PATH} ({len(results)} записей)")


if __name__ == "__main__":
    main()
