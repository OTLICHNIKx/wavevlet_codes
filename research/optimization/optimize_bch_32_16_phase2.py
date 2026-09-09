"""Этап C фаза 2 (ТЗ §7.2): BCH-derived (32,16) с другими корректными
параметрами, когда puncture-only перебор (153 пары, фаза 1) дал
максимум d=6.

Пространство поиска: родительские BCH [2^m-1, k_p, d>=dd], затем
укорочение до [n_sh,16] (s = k_p - 16 информационных координат) и
выкалывание p = n_sh - 32 проверочных координат. Конфигурации:
        (m, dd, first_root) -> [63,38,>=9] p=9; [63,36,>=9,root5] p=11;
                               [63,36,>=11] p=11
Для каждой конфигурации: сэмплирование множеств укорочения, точный
перебор shortened кода (2^16), затем локальный поиск puncture-множества
по fast-критерию min_w (wt(w) - |supp(w) ∩ P|), финальная точная
проверка полного кода.

Запуск:
    python -m research.optimization.optimize_bch_32_16_phase2 --time-limit 1500
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

import numpy as np

from bch.code import BCHCode
from bch.derived import BCHDerivedCode, build_systematic_generator_matrix

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    save_json,
)


def enumerate_supports(generator: np.ndarray, max_weight: int) -> list[tuple[int, int]]:
    """Все слова веса <= max_weight как (mask, weight)."""
    k, n = generator.shape
    assert n <= 63
    row_masks = np.zeros(k, dtype=np.int64)
    for row in range(k):
        value = 0
        for column, bit in enumerate(generator[row]):
            if bit:
                value |= 1 << column
        row_masks[row] = value
    results: list[tuple[int, int]] = []
    previous_gray = 0
    current = 0
    for counter in range(1, 1 << k):
        gray = counter ^ (counter >> 1)
        changed = previous_gray ^ gray
        bit = int(changed.bit_length() - 1)
        current ^= int(row_masks[bit])
        weight = int(current).bit_count()
        if 0 < weight <= max_weight:
            results.append((current, weight))
        previous_gray = gray
    return results


def config_info(m: int, designed_distance: int, first_root: int) -> dict[str, Any] | None:
    try:
        parent = BCHCode.primitive(
            m=m, designed_distance=designed_distance, first_root=first_root
        )
    except ValueError:
        return None
    k_p, n_p = parent.generator_matrix.shape
    s = k_p - 16
    n_sh = n_p - s
    p = n_sh - 32
    if s < 0 or p < 1 or n_sh > 63:
        return None
    sysres = build_systematic_generator_matrix(parent.generator_matrix)
    inv = {int(c): pos for pos, c in enumerate(sysres.column_permutation)}
    info_parent_coords = [c for c in range(n_p) if inv[c] < k_p]
    return {
        "m": m,
        "designed_distance": designed_distance,
        "first_root": first_root,
        "parent_k": int(k_p),
        "parent_n": int(n_p),
        "shortening_count": int(s),
        "puncture_count": int(p),
        "n_shortened": int(n_sh),
        "info_parent_coords": info_parent_coords,
    }


def search_config(
    info: dict[str, Any],
    rng: np.random.Generator,
    deadline: float,
    samples_per_config: int,
    use_trivial_filter: bool = True,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    s = info["shortening_count"]
    p = info["puncture_count"]
    n_sh = info["n_shortened"]
    parity_positions = list(range(16, n_sh))
    for sample in range(samples_per_config):
        if time.perf_counter() > deadline:
            break
        shortening = tuple(
            sorted(
                int(c)
                for c in rng.choice(info["info_parent_coords"], size=s, replace=False)
            )
        )
        try:
            shortened = BCHDerivedCode.from_primitive_parent(
                m=info["m"],
                designed_distance=info["designed_distance"],
                first_root=info["first_root"],
                shortening_count=s,
                puncture_count=0,
                shortening_coordinates=shortening,
                name="short_probe",
            )
        except ValueError:
            continue
        generator = np.asarray(shortened.generator_matrix, dtype=np.uint8)
        analysis = exact_weight_enumerator(generator)
        d_sh = analysis["d_min_exact"]
        if use_trivial_filter and d_sh - p < 7:
            continue  # потолок ниже цели — не тратим puncture-поиск
        supports = enumerate_supports(generator, max_weight=min(n_sh, d_sh + 3))
        masks = np.array([w for w, _ in supports], dtype=np.int64)
        weights = np.array([v for _, v in supports], dtype=np.int64)

        def score(puncture_set: tuple[int, ...]) -> int:
            hits = np.zeros(masks.shape[0], dtype=np.int64)
            for coordinate in puncture_set:
                hits += ((masks >> coordinate) & 1).astype(np.int64)
            return int((weights - hits).min())

        best_puncture = tuple(
            int(c) for c in rng.choice(parity_positions, size=p, replace=False)
        )
        best_value = score(best_puncture)
        stall = 0
        sample_deadline = min(deadline, time.perf_counter() + 4.0)
        while time.perf_counter() < sample_deadline and stall < 400 and best_value < 9:
            candidate = list(best_puncture)
            index = int(rng.integers(p))
            choice = int(rng.integers(len(parity_positions)))
            if parity_positions[choice] in candidate:
                stall += 1
                continue
            candidate[index] = parity_positions[choice]
            candidate = tuple(sorted(candidate))
            value = score(candidate)
            if value >= best_value:
                if value > best_value:
                    stall = 0
                else:
                    stall += 1
                best_puncture, best_value = candidate, value
            else:
                stall += 1
        try:
            final = BCHDerivedCode.from_primitive_parent(
                m=info["m"],
                designed_distance=info["designed_distance"],
                first_root=info["first_root"],
                shortening_count=s,
                puncture_count=p,
                shortening_coordinates=shortening,
                puncture_coordinates=best_puncture,
                name="bch32_candidate",
            )
        except ValueError:
            continue
        final_analysis = exact_weight_enumerator(final.generator_matrix)
        results.append(
            {
                "m": info["m"],
                "designed_distance": info["designed_distance"],
                "first_root": info["first_root"],
                "shortening_coordinates": list(shortening),
                "puncture_coordinates": list(best_puncture),
                "d_shortened": int(d_sh),
                "d_min_exact": int(final_analysis["d_min_exact"]),
                "A_dmin": int(final_analysis["A_dmin"]),
                "weight_enumerator": list(final_analysis["weight_enumerator"]),
                "fingerprint": code_fingerprint(final.generator_matrix),
            }
        )
        log(
            f"cfg m{info['m']} dd{info['designed_distance']} r{info['first_root']} "
            f"sample{sample}: d_sh={d_sh} -> d_final={final_analysis['d_min_exact']}"
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7001)
    parser.add_argument("--time-limit", type=float, default=1500.0)
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--trivial-filter", action="store_true")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    deadline = time.perf_counter() + args.time_limit
    all_results: list[dict[str, Any]] = []
    configs = [
        config_info(6, 9, 1),
        config_info(6, 11, 1),
        config_info(6, 9, 5),
    ]
    for info in configs:
        if info is None:
            continue
        log(
            f"config m={info['m']} dd={info['designed_distance']} "
            f"root={info['first_root']}: k_p={info['parent_k']} "
            f"s={info['shortening_count']} p={info['puncture_count']}"
        )
        if time.perf_counter() >= deadline:
            break
        all_results.extend(
            search_config(
                info,
                rng,
                deadline,
                args.samples,
                use_trivial_filter=args.trivial_filter,
            )
        )
    all_results.sort(key=lambda r: (-r["d_min_exact"], r["A_dmin"]))
    summary = {
        "family": "bch_derived",
        "n": 32,
        "k": 16,
        "phase": "2 — alternative valid BCH parents (§7.2)",
        "seed": args.seed,
        "results": all_results[:20],
        "results_count": len(all_results),
    }
    path = save_json("bch_32_16_phase2_candidates.json", summary)
    if all_results:
        best = all_results[0]
        log(
            f"phase2 best: d={best['d_min_exact']} "
            f"dd={best['designed_distance']} root={best['first_root']}"
        )
    else:
        log("phase2: ни один валидный кандидат не построен/не пережил фильтры")


if __name__ == "__main__":
    main()
