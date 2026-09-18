"""Уточнение d_min существующего LDPC (64,32).

Текущий результат: d_min >= 9 (сертификат), верхняя оценка 14.
Цель: найти минимальное кодовое слово (MITM точно проверяет веса
9, 10, [опционально 11]) и сузить upper bound.

Код НЕ меняется. Результаты:
research_results/distance_refinement_64_32/ldpc_64_32.json (+ results.json)

Запуск:
    python -m research.optimization.distance_refinement_64_32.refine_ldpc_64_32
    [--deep]   # добавить MITM-проверку веса 11 (6+5), долгую (~5-10 мин)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
from typing import Any

import numpy as np

from research.config import LDPC_64_32_CONFIG
from ldpc.presets import LDPC_64_32

from research.optimization.distance_refinement_64_32.syndrome_search import (
    capture_baseline,
    refine_distance,
)

RESULTS_DIR = pathlib.Path("research_results/distance_refinement_64_32")

PARAM_FIELDS = (
    "minimum_distance_exact",
    "minimum_distance_lower_bound",
    "minimum_distance_upper_bound",
    "distance_evidence",
    "verified_error_correction_radius",
)


def quick_upper_bound(generator: np.ndarray, seed: int = 77) -> dict[str, Any]:
    """Быстрая ВЕРХНЯЯ оценка: перебор сообщений веса <=2 + случайные."""
    G = np.asarray(generator, dtype=np.uint8)
    k, n = G.shape
    best = n + 1
    best_msg: tuple[int, ...] = ()
    for i in range(k):
        w = int(G[i].sum())
        if 0 < w < best:
            best, best_msg = w, (i,)
    for i in range(k):
        for j in range(i + 1, k):
            w = int((G[i] ^ G[j]).sum())
            if 0 < w < best:
                best, best_msg = w, (i, j)
    rng = np.random.default_rng(seed)
    for weight in range(3, k):
        for _ in range(2000):
            positions = rng.choice(k, size=weight, replace=False)
            word = G[list(positions)].sum(axis=0) % 2
            w = int(word.sum())
            if 0 < w < best:
                best = w
                best_msg = tuple(sorted(int(p) for p in positions))
    return {
        "found_word_weight": int(best),
        "message_positions": list(best_msg),
        "note": "random+low-weight search: only an upper estimate",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deep", action="store_true",
                        help="проверить также вес 11 (MITM 5+6)")
    args = parser.parse_args()

    code = LDPC_64_32
    baseline = capture_baseline(code)
    assert baseline["matrices_valid"] and baseline["orthogonality_GHT_zero"]

    upper = quick_upper_bound(code.generator_matrix)
    payload: dict[str, Any] = {
        "family": "ldpc",
        "name": LDPC_64_32_CONFIG.name,
        "previous_bounds": {
            field: getattr(LDPC_64_32_CONFIG, field) for field in PARAM_FIELDS
        },
        "baseline": baseline,
        "previous_upper_bound": upper,
    }

    weights = (9, 10, 11) if args.deep else (9, 10)
    start = time.perf_counter()
    result = refine_distance(
        code.generator_matrix,
        code.parity_check_matrix,
        certificate_size=4,
        candidate_weights=weights,
        progress=lambda message: print(
            f"[ldpc64] {message} ...", flush=True
        ),
    )
    result["runtime_sec"] = round(time.perf_counter() - start, 1)
    payload["refinement"] = result

    (RESULTS_DIR / "ldpc_64_32.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])

    results_path = RESULTS_DIR / "results.json"
    results = (
        json.loads(results_path.read_text(encoding="utf-8"))
        if results_path.exists()
        else {}
    )
    results["ldpc_64_32"] = {
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
        "upper_bound": upper["found_word_weight"],
        "method": (
            "syndrome certificate on all subsets <=4 (d>=9) + exact "
            "meet-in-the-middle search of dependent column sets "
            f"weights {list(weights)}"
        ),
        "runtime_sec": result.get("runtime_sec"),
    }
    results_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("saved", results_path)


if __name__ == "__main__":
    main()
