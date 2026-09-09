"""Этап D: seed-sweep для Goppa-derived (32,16) существующей конструкции
(m=5, degree=3, target_k=16) с опциональным перебором примитивных
полиномов GF(32).

Для каждого валидного derived [32,16] кандидата:
  * точный d_min и weight enumerator перебором 2^16 слов;
  * A_dmin и следующий вес (tie-break по ТЗ §11);
  * fingerprint;
  * параметры конструкции (seed, primitive_polynomial, goppa_polynomial).

Запуск:
    python -m research.optimization.optimize_goppa_32_16 --seeds 3000
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import numpy as np

from goppa.code import GoppaCode
from goppa.construction import build_goppa_construction
from goppa.derived import GoppaDerivedCode

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    matrices_valid,
    save_json,
)


def primitive_polynomials_degree5() -> list[int]:
    """
    Примитивные (они же неприводимые) полиномы степени 5 над GF(2).

    Группа GF(32)* имеет простой порядок 31, поэтому любой корень
    неприводимого полинома степени 5 примитивен: достаточно, что
    конструктор поля принимает полином и alpha^e != 1 для e = 1..30.
    """
    from bch.field import GF2m

    found: list[int] = []
    for poly in range(0b100001, 0b1000000):
        if poly & 1 == 0:
            continue
        try:
            field = GF2m(5, primitive_polynomial=poly)
        except Exception:
            continue
        alpha = field.alpha(1)
        value = 1
        has_small_order = False
        for _ in range(30):
            value = field.multiply(value, alpha)
            if value == 1:
                has_small_order = True
                break
        if not has_small_order:
            found.append(poly)
    return found


def evaluate_candidate(
    seed: int, primitive_polynomial: int | None
) -> dict[str, Any] | None:
    try:
        construction = build_goppa_construction(
            m=5, degree=3, seed=seed,
            primitive_polynomial=primitive_polynomial,
        )
        parent = GoppaCode.from_construction(construction)
        if parent.k < 16:
            return None
        derived = GoppaDerivedCode.from_parent(
            parent, target_k=16, name=f"goppa_32_16_seed{seed}"
        )
    except ValueError:
        return None
    generator = np.asarray(derived.generator_matrix, dtype=np.uint8)
    parity_check = np.asarray(derived.parity_check_matrix, dtype=np.uint8)
    if not matrices_valid(generator, parity_check, 32, 16):
        return None
    analysis = exact_weight_enumerator(generator)
    d = analysis["d_min_exact"]
    enumerator = analysis["weight_enumerator"]
    return {
        "seed": seed,
        "primitive_polynomial": primitive_polynomial,
        "parent_k": int(parent.k),
        "d_min_exact": d,
        "A_dmin": analysis["A_dmin"],
        "next_weights": list(enumerator[d + 1 : d + 4]),
        "weight_enumerator": list(enumerator),
        "fingerprint": code_fingerprint(generator),
        "goppa_polynomial": list(construction.goppa_polynomial),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=3000)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument(
        "--polynomials",
        choices=["default", "all"],
        default="all",
    )
    args = parser.parse_args()

    if args.polynomials == "all":
        polynomials = primitive_polynomials_degree5()
        log(f"primitive degree-5 polynomials: {polynomials}")
    else:
        polynomials = [None]

    results: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()
    for polynomial in polynomials:
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            record = evaluate_candidate(seed, polynomial)
            if record is None:
                continue
            if record["fingerprint"] in seen_fingerprints:
                continue
            seen_fingerprints.add(record["fingerprint"])
            results.append(record)
            if len(results) % 200 == 0:
                log(f"{len(results)} unique candidates so far")

    results.sort(
        key=lambda r: (-r["d_min_exact"], r["A_dmin"], r["next_weights"])
    )
    summary = {
        "family": "goppa_derived",
        "n": 32,
        "k": 16,
        "search": {
            "algorithm": "seed sweep of m=5, deg=3 construction x all primitive degree-5 polynomials",
            "polynomials": polynomials,
            "seeds_per_polynomial": args.seeds,
            "unique_codes": len(results),
        },
        "top": results[:10],
    }
    save_json("goppa_32_16_candidates.json", summary)
    log(
        f"best: d={results[0]['d_min_exact']} "
        f"A_d={results[0]['A_dmin']} "
        f"seed={results[0]['seed']} "
        f"poly={results[0]['primitive_polynomial']}"
    )
    from collections import Counter

    log(
        "d distribution: "
        + str(dict(sorted(Counter(r["d_min_exact"] for r in results).items())))
    )


if __name__ == "__main__":
    main()
