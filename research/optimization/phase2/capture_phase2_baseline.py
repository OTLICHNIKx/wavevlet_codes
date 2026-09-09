"""Снимок начала фазы 2: текущее состояние production-кодов (после
фазы 1) + таблица сравнения baseline -> phase1.

Запуск:
    python -m research.optimization.phase2.capture_phase2_baseline
"""

from __future__ import annotations

from typing import Any

import numpy as np

from research.code_factory import build_code_from_config
from research.config import FIVE_FAMILIES_20K_FULL_DECODERS_16_8 as FF16
from research.config import FIVE_FAMILIES_20K_FULL_DECODERS_32_16 as FF32
from research.config import FIVE_FAMILIES_20K_FULL_DECODERS_64_32 as FF64

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    matrices_valid,
    save_json,
)
from research.optimization.phase2.fast_distance import PHASE2_DIR
from ldpc import minimum_distance_certificate

PHASE1 = {
    ("wavelet", 16): {"baseline_d": 5, "phase1_d": 5},
    ("bch_derived", 16): {"baseline_d": 5, "phase1_d": 5},
    ("goppa_derived", 16): {"baseline_d": 5, "phase1_d": 5},
    ("reed_solomon_binary", 16): {"baseline_d": 5, "phase1_d": 5},
    ("ldpc", 16): {"baseline_d": 5, "phase1_d": 5},
    ("wavelet", 32): {"baseline_d": 8, "phase1_d": 8},
    ("bch_derived", 32): {"baseline_d": 5, "phase1_d": 6},
    ("goppa_derived", 32): {"baseline_d": 7, "phase1_d": 7},
    ("reed_solomon_binary", 32): {"baseline_d": 6, "phase1_d": 7},
    ("ldpc", 32): {"baseline_d": 8, "phase1_d": 8},
    ("wavelet", 64): {"baseline_d": 8, "phase1_d": ">=11"},
    ("bch_derived", 64): {"baseline_d": "9..10", "phase1_d": "9..10"},
    ("goppa_derived", 64): {"baseline_d": 9, "phase1_d": 9},
    ("reed_solomon_binary", 64): {"baseline_d": 10, "phase1_d": 10},
    ("ldpc", 64): {"baseline_d": ">=9", "phase1_d": ">=9"},
}


def capture(code_config) -> dict[str, Any]:
    code = build_code_from_config(code_config)
    generator = np.asarray(code.generator_matrix, dtype=np.uint8)
    parity_check = np.asarray(code.parity_check_matrix, dtype=np.uint8)
    entry: dict[str, Any] = {
        "family": code_config.family,
        "name": code_config.name,
        "n": code.n,
        "k": code.k,
        "matrices_valid": matrices_valid(generator, parity_check, code.n, code.k),
        "fingerprint": code_fingerprint(generator),
    }
    if code.k <= 16:
        analysis = exact_weight_enumerator(generator)
        entry["d_min_exact"] = int(analysis["d_min_exact"])
        entry["A_dmin"] = int(analysis["A_dmin"])
    else:
        bound4 = minimum_distance_certificate(parity_check, 4)
        bound5 = minimum_distance_certificate(parity_check, 5)
        entry["certificate_d_ge"] = max(bound4, bound5)
    return entry


def main() -> None:
    snapshot: dict[str, Any] = {}
    comparison: list[dict[str, Any]] = []
    for config, label in ((FF16, "16_8"), (FF32, "32_16"), (FF64, "64_32")):
        entries = []
        for code_config in config.codes:
            entry = capture(code_config)
            entries.append(entry)
            key = (entry["family"], entry["n"])
            info = PHASE1.get(key, {})
            comparison.append(
                {
                    "family": entry["family"],
                    "n": entry["n"],
                    "k": entry["k"],
                    "phase1_d": entry.get("d_min_exact", entry.get("certificate_d_ge")),
                    "phase1_A_dmin": entry.get("A_dmin"),
                    "fingerprint": entry["fingerprint"],
                }
            )
        snapshot[label] = entries
    save_json("baseline.json", {"phase2_start": snapshot}, directory=PHASE2_DIR)
    save_json(
        "phase1_comparison.json", {"rows": comparison}, directory=PHASE2_DIR
    )
    for row in comparison:
        log(f"{row['family']:<20} {row['n']},{row['k']} -> d={row['phase1_d']}")


if __name__ == "__main__":
    main()
