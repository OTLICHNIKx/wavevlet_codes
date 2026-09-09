"""Этап C: полный перебор всех C(18,2)=153 пар puncture-координат для
BCH-derived (32,16) на базе текущей конструкции

    BCH(63,45,d>=7) -> shorten 29 -> [34,16] -> puncture 2 -> [32,16].

Для каждого кандидата: точный d_min и полный weight enumerator
перебором всех 2^16 слов, tie-break по A_dmin и следующему весу
(ТЗ §11). При недостатке puncture-only поиска предусмотрена фаза 2
(другие корректные BCH-параметры).

Запуск:
    python -m research.optimization.optimize_bch_32_16
"""

from __future__ import annotations

import itertools
import json
from typing import Any

import numpy as np

from bch.derived import BCHDerivedCode

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    matrices_valid,
    save_json,
)

PARENT = dict(m=6, designed_distance=7, shortening_count=29, puncture_count=2)
PARITY_COORDINATES = tuple(range(16, 34))  # [34,16]: 16 parity-позиций
BASELINE = {
    "puncture_coordinates": None,  # default (последние 2)
    "d_min_exact": 5,
    "fingerprint": "b64120fd51867c0a",
}


def build_candidate(puncture_coordinates: tuple[int, int]) -> dict[str, Any]:
    try:
        code = BCHDerivedCode.from_primitive_parent(
            **PARENT,
            puncture_coordinates=puncture_coordinates,
            name=f"bch_derived_32_16_{puncture_coordinates[0]}_{puncture_coordinates[1]}",
        )
    except ValueError as error:
        return {"error": str(error), "puncture_coordinates": puncture_coordinates}
    generator = np.asarray(code.generator_matrix, dtype=np.uint8)
    parity_check = np.asarray(code.parity_check_matrix, dtype=np.uint8)
    if not matrices_valid(generator, parity_check, 32, 16):
        return {"error": "invalid matrices", "puncture_coordinates": puncture_coordinates}
    analysis = exact_weight_enumerator(generator)
    enumerator = analysis["weight_enumerator"]
    d = analysis["d_min_exact"]
    tail = tuple(enumerator[d + 1 : d + 4])
    return {
        "puncture_coordinates": list(puncture_coordinates),
        "d_min_exact": d,
        "A_dmin": analysis["A_dmin"],
        "next_weights_A_d1_d2_d3": list(tail),
        "weight_enumerator": list(enumerator),
        "fingerprint": code_fingerprint(generator),
    }


def main() -> None:
    results: list[dict[str, Any]] = []
    for pair in itertools.combinations(PARITY_COORDINATES, 2):
        record = build_candidate(pair)
        results.append(record)
        if "error" not in record:
            log(
                f"pair {pair}: d={record['d_min_exact']} "
                f"A_d={record['A_dmin']} fp={record['fingerprint']}"
            )

    valid = [r for r in results if "error" not in r]
    valid.sort(
        key=lambda r: (
            -r["d_min_exact"],
            r["A_dmin"],
            r["next_weights_A_d1_d2_d3"],
        )
    )
    summary = {
        "family": "bch_derived",
        "n": 32,
        "k": 16,
        "baseline": BASELINE,
        "search": {
            "algorithm": "exhaustive over all C(18,2)=153 parity puncture pairs",
            "pairs_evaluated": len(results),
            "valid": len(valid),
            "errors": len(results) - len(valid),
        },
        "top": valid[:10],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    save_json("bch_32_16_candidates.json", summary)
    if valid:
        best = valid[0]
        log(
            f"BEST: puncture={best['puncture_coordinates']} "
            f"d={best['d_min_exact']} A_d={best['A_dmin']}"
        )
    else:
        log("no valid candidates")


if __name__ == "__main__":
    main()
