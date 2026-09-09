"""Фаза 2 для Goppa-derived (32,16): цель d_min >= 8, бюджет >= 10000 seed.

Расширение поиска по ТЗ §4 без изменения алгоритма Goppa:
  * seed sweep: до --seeds случайных детерминированных seed на каждый
    из 6 примитивных полиномов GF(32);
  * вариант construction-параметров: deg=3, support=GF(32) (другие deg
    не дают parent k>=16: deg=4 -> k<=12, что проверено конструкцией);
  * все уникальные derived-коды: точный d_min + весовой enumerator
    (2^16 полный перебор), A_dmin, fingerprint;
  * отдельно: для лучших parent-кодов перебираются ВСЕ гиперплоскостные
    16-мерные subcodes (derivation alternative) — есть ли d=8 среди них.

Запуск:
    python -m research.optimization.phase2.optimize_goppa_phase2 --seeds 2000
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from bch import gf2_matrix_rank
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
from research.optimization.phase2.fast_distance import PHASE2_DIR
from research.optimization.optimize_goppa_32_16 import (
    primitive_polynomials_degree5,
)

PHASE1_BEST_FP = "efdc15c1f5794c87"  # baseline (m=5,deg=3,seed=42)
KNOWN_TOP = {"d": 7, "A_d": 95, "fingerprint": None}


def evaluate(m: int, degree: int, seed: int, polynomial: int | None) -> dict[str, Any] | None:
    try:
        construction = build_goppa_construction(
            m=m, degree=degree, seed=seed, primitive_polynomial=polynomial
        )
        parent = GoppaCode.from_construction(construction)
        if parent.k < 16:
            return None
        derived = GoppaDerivedCode.from_parent(
            parent, target_k=16, name=f"goppa_{seed}_{polynomial}"
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
        "polynomial": polynomial,
        "parent_k": int(parent.k),
        "d": int(d),
        "A_d": int(analysis["A_dmin"]),
        "A_next": [int(enumerator[d + i]) if d + i <= 32 else 0 for i in (1, 2)],
        "weight_enumerator": list(enumerator),
        "fingerprint": code_fingerprint(generator),
        "goppa_polynomial": list(construction.goppa_polynomial),
    }


def hyperplane_probe(top_parents: list[dict[str, Any]], budget: int = 30) -> dict[str, Any]:
    """
    Для лучших parent-кодов: существует ли 16-мерный subcode с d>=8?
    Перебор гиперплоскостей = выбор nonzero linear functional f на
    parent C (dim 17): ker f ∩ C. Проверка: все слова веса 7 (в parent)
    должны быть НЕ в ker f => f не обнуляет ни одно 7-слово.
    Ищем f: это вектор из GF(2)^17 вне объединения гиперплоскостей
    7-слов — случайный поиск с точной проверкой.
    """
    result: dict[str, Any] = {"attempted": 0, "found": False}
    rng = np.random.default_rng(7)
    for parent_record in top_parents[:budget]:
        try:
            construction = build_goppa_construction(
                m=5,
                degree=3,
                seed=parent_record["seed"],
                primitive_polynomial=parent_record["polynomial"],
            )
            parent = GoppaCode.from_construction(construction)
        except ValueError:
            continue
        G = np.asarray(parent.generator_matrix, dtype=np.uint8)
        k_parent = G.shape[0]
        if k_parent != 17:
            continue
        # все слова веса 7 в parent: перебор сообщений веса до 3
        # (7-слово может быть из сообщения любого веса — но переберём
        # 2^17 полностью: 131072, маски int64)
        row_masks = np.array(
            [int("".join(map(str, row[::-1])), 2) for row in G], dtype=object
        )
        seven_words_messages: list[int] = []
        previous = 0
        current = 0
        for counter in range(1, 1 << k_parent):
            gray = counter ^ (counter >> 1)
            bit = (gray ^ previous).bit_length() - 1
            current ^= int(row_masks[bit])
            if current.bit_count() == 7:
                # СООБЩЕНИЕ равно gray (не counter) — слово в code
                # соответствует именно этому вектору сообщений.
                seven_words_messages.append(gray)
            previous = gray
        if not seven_words_messages:
            result.setdefault("parents_without_weight7", 0)
            result["parents_without_weight7"] += 1
            continue
        result["attempted"] += 1
        W7 = np.array(
            [[(m_ >> b) & 1 for b in range(k_parent)] for m_ in seven_words_messages],
            dtype=np.uint8,
        )
        rank7 = int(gf2_matrix_rank(W7))
        result.setdefault("parents", []).append(
            {
                "seed": parent_record["seed"],
                "polynomial": parent_record["polynomial"],
                "num_weight7_words": len(seven_words_messages),
                "rank_of_weight7_span": rank7,
            }
        )
        # hyperplane ker f: f: GF(2)^17 -> GF(2), f(message)=f·msg.
        # Нужно f с f(w) = 1 для ВСЕХ 7-слов w (тогда ни одно 7-слово
        # не попадёт в ker). Линейная система f·w=1 над GF(2).
        W = np.array(
            [[(m_ >> b) & 1 for b in range(k_parent)] for m_ in seven_words_messages],
            dtype=np.uint8,
        )
        f = _solve_affine_gf2(W, np.ones(W.shape[0], dtype=np.uint8))
        if f is None:
            # Система f·w = 1 для всех 7-слов НЕРЕШИМА => каждая
            # гиперплоскость (ядро nonzero формы) содержит 7-слово,
            # т.е. d=8 НЕВОЗМОЖЕН ни в одном 16-мерном subcode этого
            # parent — строгое доказательство, а не неудача эвристики.
            log(
                f"hyperplane probe: parent seed={parent_record['seed']} "
                f"poly={parent_record['polynomial']}: impossibility "
                "certified for this parent"
            )
            continue
        result["found"] = True
        # базис ядра линейной формы f: pivot p (f[p]=1), строки
        # e_i + f[i]·e_p для i != p => 16 независимых векторов ker f.
        pivot = int(np.flatnonzero(f == 1)[0])
        rows = []
        for i in range(k_parent):
            if i == pivot:
                continue
            vector = np.zeros(k_parent, dtype=np.uint8)
            vector[i] = 1
            vector[pivot] = int(f[i])
            rows.append(vector)
        null_basis = np.vstack(rows).astype(np.uint8)
        G_sub = (
            null_basis.astype(np.int64) @ G.astype(np.int64) % 2
        ).astype(np.uint8)
        analysis = exact_weight_enumerator(G_sub)
        entry = {
            "seed": parent_record["seed"],
            "polynomial": parent_record["polynomial"],
            "functional": [int(v) for v in f],
            "num_weight7_words": len(seven_words_messages),
            "subcode_d": int(analysis["d_min_exact"]),
            "subcode_A_d": int(analysis["A_dmin"]),
            "subcode_fingerprint": code_fingerprint(G_sub),
            "weight_enumerator": list(analysis["weight_enumerator"]),
        }
        result.setdefault("subcodes", []).append(entry)
        log(
            f"hyperplane probe: parent seed={parent_record['seed']} "
            f"A7={len(seven_words_messages)} -> subcode d={entry['subcode_d']} "
            f"A_d={entry['subcode_A_d']} fp={entry['subcode_fingerprint']}"
        )
    if result.get("subcodes"):
        result["subcodes"].sort(key=lambda e: (-e["subcode_d"], e["subcode_A_d"]))
    return result


def _solve_affine_gf2(A: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    """Решение A f = b над GF(2) (одна строка f длиной k)."""
    m, n = A.shape
    M = np.hstack([A.astype(np.uint8), b.reshape(-1, 1).astype(np.uint8)]).copy()
    pivots: list[int] = []
    row = 0
    for col in range(n):
        candidates = np.flatnonzero(M[row:, col])
        if candidates.size == 0:
            continue
        selected = row + int(candidates[0])
        M[[row, selected]] = M[[selected, row]]
        for r in range(m):
            if r != row and M[r, col]:
                M[r] ^= M[row]
        pivots.append(col)
        row += 1
    inconsistent = np.flatnonzero(
        (M[:, :n] == 0).all(axis=1) & (M[:, n] == 1)
    )
    if inconsistent.size:
        return None
    f = np.zeros(n, dtype=np.uint8)
    # свободные переменные = 0, pivot = rhs
    for index, col in enumerate(pivots):
        f[col] = M[index, n]
    if not np.all((A.astype(np.int64) @ f.astype(np.int64)) % 2 == 1):
        return None
    return f


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=2000,
                        help="seeds per polynomial (6 polynomials => 6*seeds total)")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--resume-every", type=int, default=250)
    args = parser.parse_args()

    polynomials = primitive_polynomials_degree5()
    total = len(polynomials) * args.seeds
    log(f"sweep {total} candidates over polynomials {polynomials}")

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    start = time.perf_counter()
    checkpoint_path = PHASE2_DIR / "goppa_phase2_partial.json"
    PHASE2_DIR.mkdir(parents=True, exist_ok=True)
    for polynomial in polynomials:
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            record = evaluate(5, 3, seed, polynomial)
            if record is None:
                continue
            if record["fingerprint"] in seen:
                continue
            seen.add(record["fingerprint"])
            results.append(record)
        if polynomial is not None:
            checkpoint = {
                "polynomials_done": True,
                "current": polynomial,
                "unique_codes": len(results),
                "d_distribution": dict(Counter(r["d"] for r in results)),
                "elapsed_sec": round(time.perf_counter() - start, 1),
            }
            checkpoint_path.write_text(
                json.dumps(checkpoint, indent=2), encoding="utf-8"
            )
            log(
                f"poly {polynomial}: unique={len(results)} "
                f"d_dist={dict(Counter(r['d'] for r in results))}"
            )
    results.sort(key=lambda r: (-r["d"], r["A_d"], r["A_next"]))

    top_parents = [r for r in results if r["parent_k"] >= 16][:40]
    hyper = hyperplane_probe(top_parents)

    payload = {
        "family": "goppa_derived",
        "n": 32,
        "k": 16,
        "target": 8,
        "reached_target": bool(results and results[0]["d"] >= 8),
        "budget_seeds_total": total,
        "unique_codes": len(results),
        "elapsed_sec": round(time.perf_counter() - start, 1),
        "d_distribution": dict(Counter(r["d"] for r in results)),
        "top": results[:10],
        "hyperplane_probe": hyper,
    }
    path = save_json("goppa_phase2_candidates.json", payload, directory=PHASE2_DIR)
    log(f"saved {path}")
    if results:
        log(
            f"goppa best: d={results[0]['d']} A={results[0]['A_d']} "
            f"seed={results[0]['seed']} poly={results[0]['polynomial']}"
        )


if __name__ == "__main__":
    main()
