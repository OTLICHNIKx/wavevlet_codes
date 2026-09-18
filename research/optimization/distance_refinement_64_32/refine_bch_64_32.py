"""Уточнение d_min существующего BCH-derived (64,32).

Текущий результат: 9 <= d_min <= 10.
Цель: найти слово веса 9 (=> d_min=9 exact) либо доказать отсутствие
слов веса 9 и найти слово веса 10 (=> d_min=10 exact).

Код НЕ меняется — только измеряется. Результаты:
research_results/distance_refinement_64_32/bch_64_32.json (+ results.json)

Запуск:
    python -m research.optimization.distance_refinement_64_32.refine_bch_64_32
"""

from __future__ import annotations

import json
import time
from typing import Any

from research.code_factory import build_code_from_config
from research.config import (
    BCH_DERIVED_64_32_CONFIG,
    FOUR_FAMILY_BCH_DERIVED_64_32_CONFIG,
)

from research.optimization.distance_refinement_64_32.syndrome_search import (
    capture_baseline,
    refine_distance,
)

RESULTS_DIR = "research_results/distance_refinement_64_32"

PARAM_FIELDS = (
    "bch_m",
    "bch_designed_distance",
    "bch_first_root",
    "bch_shortening_count",
    "bch_puncture_count",
    "bch_puncture_coordinates",
    "minimum_distance_exact",
    "minimum_distance_lower_bound",
    "minimum_distance_upper_bound",
    "distance_evidence",
    "verified_error_correction_radius",
)


def main() -> None:
    code = build_code_from_config(BCH_DERIVED_64_32_CONFIG)
    four_family_code = build_code_from_config(
        FOUR_FAMILY_BCH_DERIVED_64_32_CONFIG
    )
    baseline = capture_baseline(code)
    assert baseline["matrices_valid"] and baseline["orthogonality_GHT_zero"]
    assert (
        baseline["fingerprint_G"] == capture_baseline(four_family_code)[
            "fingerprint_G"
        ]
    ), "bch_derived_64_32 и four-family версия различаются"

    payload: dict[str, Any] = {
        "family": "bch_derived",
        "name": BCH_DERIVED_64_32_CONFIG.name,
        "previous_bounds": {
            "minimum_distance_exact": FOUR_FAMILY_BCH_DERIVED_64_32_CONFIG.minimum_distance_exact,
            "minimum_distance_lower_bound": FOUR_FAMILY_BCH_DERIVED_64_32_CONFIG.minimum_distance_lower_bound,
            "minimum_distance_upper_bound": FOUR_FAMILY_BCH_DERIVED_64_32_CONFIG.minimum_distance_upper_bound,
            "evidence": FOUR_FAMILY_BCH_DERIVED_64_32_CONFIG.distance_evidence,
        },
        "construction_parameters": {
            field: getattr(BCH_DERIVED_64_32_CONFIG, field)
            for field in PARAM_FIELDS
        },
        "baseline": baseline,
    }

    start = time.perf_counter()
    result = refine_distance(
        code.generator_matrix,
        code.parity_check_matrix,
        certificate_size=4,
        candidate_weights=(9, 10),
        progress=lambda message: print(
            f"[bch64] {message} ...", flush=True
        ),
    )
    result["runtime_sec"] = round(time.perf_counter() - start, 1)
    payload["refinement"] = result

    with open(f"{RESULTS_DIR}/bch_64_32.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])

    # merge into results.json
    import pathlib

    results_path = pathlib.Path(RESULTS_DIR) / "results.json"
    results = (
        json.loads(results_path.read_text(encoding="utf-8"))
        if results_path.exists()
        else {}
    )
    results["bch_derived_64_32"] = {
        "previous": payload["previous_bounds"],
        "baseline_fingerprint": baseline["fingerprint_G"],
        **{
            key: result.get(key)
            for key in (
                "status",
                "d_min_exact",
                "d_min_lower_bound",
                "A_dmin",
                "min_support",
                "min_message",
                "min_codeword",
                "cleared_weights",
                "certificate",
            )
        },
        "method": (
            "syndrome certificate on all subsets <=4 (d>=9) + exact "
            "meet-in-the-middle search of dependent column sets of "
            "weight 9 (4+5 split) and 10 (5+5 self-collision)"
        ),
        "runtime_sec": result.get("runtime_sec"),
    }
    results_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("saved", results_path)


if __name__ == "__main__":
    main()
