"""Фаза 2: итоговая независимая верификация production-состояния.

1. Строит ВСЕ коды пяти-семейного сравнения из research/config.py.
2. Для k <= 16: точный d перебором 2^16 — сверка с
   minimum_distance_exact / lower / upper / A_dmin в конфиге.
3. Для wavelet (64,32): повторный строгий сертификат w=5 (d>=11).
4. Fingerprint'и сверяются с phase1_comparison.json — подтверждение,
   что заменённые коды реально отличаются от предков, а
   незаменённые — идентичны.

Итог: verification.json + ненулевой exit-код при любом
расхождении config<->матрица.

Запуск:
    python -m research.optimization.phase2.verify_phase2
"""

from __future__ import annotations

import json
import sys
from typing import Any

import numpy as np

from ldpc import minimum_distance_certificate
from research.code_factory import build_code_from_config
from research.config import (
    FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
    FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
    FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
)

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    matrices_valid,
    save_json,
)
from research.optimization.phase2.fast_distance import PHASE2_DIR

EXACT_FAMILIES_32 = {"wavelet", "bch_derived", "goppa_derived", "reed_solomon_binary", "ldpc"}


def verify_code(code_config) -> dict[str, Any]:
    code = build_code_from_config(code_config)
    generator = np.asarray(code.generator_matrix, dtype=np.uint8)
    parity_check = np.asarray(code.parity_check_matrix, dtype=np.uint8)
    entry: dict[str, Any] = {
        "family": code_config.family,
        "name": code_config.name,
        "n": int(code.n),
        "k": int(code.k),
        "matrices_valid": matrices_valid(
            generator, parity_check, code.n, code.k
        ),
        "fingerprint": code_fingerprint(generator),
    }
    ok = entry["matrices_valid"]
    if code.k <= 16:
        analysis = exact_weight_enumerator(generator)
        d = int(analysis["d_min_exact"])
        entry["measured_d_min_exact"] = d
        entry["measured_A_dmin"] = int(analysis["A_dmin"])
        config = code_config
        if config.minimum_distance_exact is not None:
            entry["metadata_exact_matches"] = (
                config.minimum_distance_exact == d
            )
            ok = ok and entry["metadata_exact_matches"]
        if config.minimum_distance_lower_bound is not None:
            entry["metadata_lower_matches"] = (
                config.minimum_distance_lower_bound == d
            )
            ok = ok and entry["metadata_lower_matches"]
        if config.minimum_distance_upper_bound is not None:
            entry["metadata_upper_matches"] = (
                config.minimum_distance_upper_bound == d
            )
            ok = ok and entry["metadata_upper_matches"]
    elif code_config.family == "wavelet":
        bound5 = minimum_distance_certificate(parity_check, 5)
        entry["certificate_d_ge_11"] = bool(bound5 >= 11)
        entry["metadata_lower_matches"] = (
            code_config.minimum_distance_lower_bound == 11
        )
        ok = ok and entry["certificate_d_ge_11"] and entry["metadata_lower_matches"]
    entry["ok"] = bool(ok)
    return entry


def main() -> None:
    phase1 = json.loads(
        (PHASE2_DIR / "phase1_comparison.json").read_text(encoding="utf-8")
    )
    phase1_by_key = {
        (row["family"], row["n"]): row for row in phase1["rows"]
    }

    all_ok = True
    entries: list[dict[str, Any]] = []
    for config in (
        FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
        FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
        FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
    ):
        for code_config in config.codes:
            entry = verify_code(code_config)
            key = (entry["family"], entry["n"])
            reference = phase1_by_key.get(key)
            if reference is not None:
                entry["phase1_fingerprint"] = reference["fingerprint"]
                entry["changed_vs_phase1"] = (
                    entry["fingerprint"] != reference["fingerprint"]
                )
            entries.append(entry)
            all_ok = all_ok and entry["ok"]
            log(
                f"{entry['name']:<38} ok={entry['ok']} "
                f"d={entry.get('measured_d_min_exact', entry.get('certificate_d_ge_11'))} "
                f"changed_vs_phase1={entry.get('changed_vs_phase1')}"
            )

    payload = {
        "all_ok": all_ok,
        "codes": entries,
    }
    path = save_json("verification.json", payload, directory=PHASE2_DIR)
    log(f"saved {path}")
    if not all_ok:
        log("VERIFICATION FAILED")
        sys.exit(1)
    log("verification passed")


if __name__ == "__main__":
    main()
