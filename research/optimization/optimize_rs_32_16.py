"""Этап E: оптимизация Reed-Solomon binary (32,16) — бинарный образ
GRS(8,4) над GF(16), m=4, primitive_polynomial=0b10011.

Фаза 1 (реализована): column_multipliers при фиксированных
evaluation_points (0..7). Фаза 2 (опция --with-points): локальный
обмен evaluation_points.

Оценка каждого кандидата — точный d_min и полный весовой enumerатор
бинарного [32,16] кода перебором 2^16 слов. Tie-break: A_dmin,
A_{d+1}, ... (ТЗ §11).

Запуск:
    python -m research.optimization.optimize_rs_32_16 --time-limit 1200
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

import numpy as np

from reed_solomon import ReedSolomonBinaryCode

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    save_json,
)

M = 4
SYMBOL_N = 8
SYMBOL_K = 4
PRIMITIVE_POLYNOMIAL = 0b10011
DEFAULT_POINTS = (0, 1, 2, 3, 4, 5, 6, 7)


def build_and_measure(
    multipliers: tuple[int, ...],
    points: tuple[int, ...],
) -> dict[str, Any] | None:
    try:
        code = ReedSolomonBinaryCode.from_parameters(
            m=M,
            symbol_n=SYMBOL_N,
            symbol_k=SYMBOL_K,
            primitive_polynomial=PRIMITIVE_POLYNOMIAL,
            evaluation_points=points,
            column_multipliers=multipliers,
            name="rs_probe",
        )
    except ValueError:
        return None
    analysis = exact_weight_enumerator(code.generator_matrix)
    d = analysis["d_min_exact"]
    enumerator = analysis["weight_enumerator"]
    return {
        "d": d,
        "A_d": analysis["A_dmin"],
        "A_d1": enumerator[d + 1] if d + 1 <= 32 else 0,
        "A_d2": enumerator[d + 2] if d + 2 <= 32 else 0,
        "weight_enumerator": list(enumerator),
        "fingerprint": code_fingerprint(code.generator_matrix),
    }


def key_of(record: dict[str, Any]) -> tuple:
    return (-record["d"], record["A_d"], record["A_d1"], record["A_d2"])


def anneal(
    seed: int,
    time_budget: float,
    with_points: bool,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    start = time.perf_counter()
    points = list(DEFAULT_POINTS)
    multipliers = [int(rng.integers(1, 16)) for _ in range(SYMBOL_N)]
    current = build_and_measure(tuple(multipliers), tuple(points))
    if current is None:
        raise RuntimeError("стартовый кандидат нестроим")
    best = dict(current)
    best["multipliers"] = list(multipliers)
    best["evaluation_points"] = list(points)
    evaluations = 1
    temperature = 3.0
    while time.perf_counter() - start < time_budget:
        progress = (time.perf_counter() - start) / time_budget
        temperature = 3.0 * (1.0 - progress) + 0.05
        candidate_multipliers = list(multipliers)
        candidate_points = list(points)
        moves = 1 if rng.random() < 0.8 else 2
        for _ in range(moves):
            change_points = with_points and rng.random() < 0.25
            if change_points:
                index = int(rng.integers(SYMBOL_N))
                choices = [v for v in range(16) if v not in candidate_points]
                if not choices:
                    continue
                candidate_points[index] = int(rng.choice(choices))
            else:
                candidate_points = list(points)
                index = int(rng.integers(SYMBOL_N))
                candidate_multipliers[index] = int(rng.integers(1, 16))
        record = build_and_measure(
            tuple(candidate_multipliers), tuple(candidate_points)
        )
        evaluations += 1
        if record is None:
            continue
        delta = sum(
            (a - b) * w
            for a, b, w in zip(
                key_of(record), key_of(current), (1000000, 1000, 10, 1)
            )
        )
        if delta <= 0 or rng.random() < np.exp(-delta / (temperature * 1000)):
            multipliers = candidate_multipliers
            points = candidate_points
            current = record
        if key_of(record) < key_of(best):
            best = dict(record)
            best["multipliers"] = list(multipliers)
            best["evaluation_points"] = list(points)
            log(
                f"best d={best['d']} A_d={best['A_d']} "
                f"mult={best['multipliers']} fp={best['fingerprint']}"
            )
    best["evaluations"] = evaluations
    best["elapsed_sec"] = time.perf_counter() - start
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260909)
    parser.add_argument("--time-limit", type=float, default=1200.0)
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--with-points", action="store_true")
    args = parser.parse_args()

    results = []
    per_chain = args.time_limit / max(1, args.chains)
    for chain in range(args.chains):
        log(f"chain {chain} start (seed {args.seed + chain})")
        best = anneal(
            seed=args.seed + chain,
            time_budget=per_chain,
            with_points=args.with_points,
        )
        results.append(best)

    results.sort(key=key_of)
    summary = {
        "family": "reed_solomon_binary",
        "n": 32,
        "k": 16,
        "construction": {
            "m": M,
            "symbol_n": SYMBOL_N,
            "symbol_k": SYMBOL_K,
            "primitive_polynomial": PRIMITIVE_POLYNOMIAL,
            "points_varied": bool(args.with_points),
        },
        "search": {
            "algorithm": "simulated annealing over column_multipliers"
            + (" + evaluation_points" if args.with_points else ""),
            "chains": args.chains,
            "seed": args.seed,
            "evaluations": sum(r.get("evaluations", 0) for r in results),
        },
        "top": results[:5],
    }
    print(json.dumps(summary["top"][0], indent=2, ensure_ascii=False))
    path = save_json("rs_32_16_candidates.json", summary)
    log(f"saved: {path}")


if __name__ == "__main__":
    main()
