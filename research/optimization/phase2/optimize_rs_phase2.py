"""Фаза 2 для Reed-Solomon binary (32,16): цель d_min >= 8.

Новые измерения поиска по ТЗ §3:
  * базис поля / отображение GF(16)->GF(2): обе примитивные
    representations x^4+x+1 (0b10011) и x^4+x^3+1 (0b11001);
  * alternative embeddings через сдвиг показателей: point set =
    {0} ∪ {alpha^i mod 15} произвольных 7 показателей (не только 0..6);
  * column multipliers: hill climbing + случайные рестарты,
    точная оценка d перебором ВСЕХ 2^16 бинарных слов (fast WordSet).

Каждый финальный кандидат: production ReedSolomonBinaryCode +
exact_weight_enumerator + fingerprint.

Запуск:
    python -m research.optimization.phase2.optimize_rs_phase2 --time-limit 2400
"""

from __future__ import annotations

import argparse
import random
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
from research.optimization.phase2.fast_distance import PHASE2_DIR

BASELINE_FP = "76df1282447f05d9"  # исходный d=6
PHASE1_FP = "e0f4d1f05cc196bb"    # фаза 1: d=7, A=28
PHASE1 = {
    "multipliers": [4, 6, 13, 7, 8, 12, 15, 10],
    "points": list(range(8)),
    "polynomial": 0b10011,
    "d": 7,
    "A_d": 28,
}


def build_code(
    multipliers: tuple[int, ...],
    points: tuple[int, ...],
    polynomial: int,
):
    try:
        return ReedSolomonBinaryCode.from_parameters(
            m=4,
            symbol_n=8,
            symbol_k=4,
            primitive_polynomial=polynomial,
            evaluation_points=points,
            column_multipliers=multipliers,
            name="rs_phase2",
        )
    except ValueError:
        return None


def score_candidate(
    multipliers: tuple[int, ...],
    points: tuple[int, ...],
    polynomial: int,
) -> dict[str, Any] | None:
    code = build_code(multipliers, points, polynomial)
    if code is None:
        return None
    analysis = exact_weight_enumerator(code.generator_matrix)
    d = analysis["d_min_exact"]
    enumerator = analysis["weight_enumerator"]
    return {
        "d": int(d),
        "A_d": int(analysis["A_dmin"]),
        "A_d1": int(enumerator[d + 1]) if d + 1 <= 32 else 0,
        "weight_enumerator": list(enumerator),
        "multipliers": list(multipliers),
        "points": list(points),
        "polynomial": polynomial,
        "fingerprint": code_fingerprint(code.generator_matrix),
    }


def key_of(record: dict[str, Any]) -> tuple:
    return (-record["d"], record["A_d"], record["A_d1"])


def anneal_chain(
    rng: random.Random,
    deadline: float,
    start_record: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    current = dict(start_record)
    best = dict(current)
    evaluations = 1
    while time.perf_counter() < deadline:
        multipliers = list(current["multipliers"])
        points = list(current["points"])
        polynomial = current["polynomial"]
        roll = rng.random()
        if roll < 0.6:
            index = rng.randrange(8)
            candidate_mult = rng.randrange(1, 16)
            if candidate_mult == multipliers[index]:
                continue
            multipliers[index] = candidate_mult
        elif roll < 0.9:
            index = rng.randrange(1, 8)
            choices = [v for v in range(16) if v not in points]
            points[index] = rng.choice(choices)
        else:
            polynomial = 0b11001 if polynomial == 0b10011 else 0b10011
        record = score_candidate(
            tuple(multipliers), tuple(points), polynomial
        )
        evaluations += 1
        if record is None:
            continue
        if key_of(record) <= key_of(current) or rng.random() < 0.03:
            current = record
        if key_of(record) < key_of(best):
            best = dict(record)
            log(
                f"rs best d={best['d']} A_d={best['A_d']} "
                f"poly={hex(best['polynomial'])} "
                f"mult={best['multipliers']}"
            )
    return best, evaluations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=314001)
    parser.add_argument("--time-limit", type=float, default=2400.0)
    parser.add_argument("--chains", type=int, default=6)
    args = parser.parse_args()

    deadline = time.perf_counter() + args.time_limit
    rng = random.Random(args.seed)
    results: list[dict[str, Any]] = []
    total_evaluations = 0

    seed_states = [
        score_candidate(
            tuple(PHASE1["multipliers"]),
            tuple(PHASE1["points"]),
            PHASE1["polynomial"],
        )
    ]
    # дополнительные точки старта: базис 25 с дефолтными мультипликаторами
    for polynomial in (0b10011, 0b11001):
        record = score_candidate(tuple([1] * 8), tuple(range(8)), polynomial)
        if record:
            seed_states.append(record)
    seed_states = [s for s in seed_states if s]
    for chain in range(args.chains):
        start = dict(seed_states[chain % len(seed_states)])
        log(f"chain {chain} start d={start['d']}")
        best, evaluations = anneal_chain(rng, deadline, start)
        total_evaluations += evaluations
        results.append(best)
        if time.perf_counter() >= deadline:
            break

    results = [r for r in results if r]
    results.sort(key=key_of)
    payload = {
        "family": "reed_solomon_binary",
        "n": 32,
        "k": 16,
        "target": 8,
        "reached_target": bool(results and results[0]["d"] >= 8),
        "seed": args.seed,
        "evaluations": total_evaluations,
        "phase1_reference": {"d": 7, "A_d": 28, "fingerprint": PHASE1_FP},
        "best": results[:8],
    }
    path = save_json("rs_phase2_candidates.json", payload, directory=PHASE2_DIR)
    log(f"saved {path}")
    if results:
        log(
            f"rs phase2 best: d={results[0]['d']} A_d={results[0]['A_d']} "
            f"poly={hex(results[0]['polynomial'])}"
        )


if __name__ == "__main__":
    main()
