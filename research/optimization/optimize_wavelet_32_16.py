"""Оптимизация wavelet_32_16: поиск (h, g, shift) с минимальным A_dmin.

Для k=16 полный перебор 2^16 слов точен и быстр (~0.1с на код).
Ищем коды с d_min >= 8 и минимальным A_8.

Запуск:
    python -m research.optimization.optimize_wavelet_32_16 --time-limit 300
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from typing import Any

import numpy as np

from wavelet import WaveletCode

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    save_json,
)

BASELINE_FINGERPRINT = "335caff4c2b02684"
BASELINE_A_D = 368
BASELINE_D_MIN = 8


def build_wavelet(
    h: tuple[int, ...],
    g: tuple[int, ...] | None,
    shift: int,
) -> WaveletCode | None:
    try:
        return WaveletCode.from_scaling_coefficients(
            h=h,
            g=g,
            codeword_length=32,
            field=2,
            a=1,
            b=1,
            shift=shift,
            name="wavelet_32_16_candidate",
        )
    except ValueError:
        return None


def score(h: tuple[int, ...], g: tuple[int, ...] | None, shift: int) -> dict[str, Any] | None:
    code = build_wavelet(h, g, shift)
    if code is None:
        return None
    result = exact_weight_enumerator(code.generator_matrix)
    fingerprint = code_fingerprint(code.generator_matrix)
    return {
        "h": list(h),
        "g": list(g) if g is not None else None,
        "shift": shift,
        "d_min": result["d_min_exact"],
        "A_dmin": result["A_dmin"],
        "weight_enumerator": list(result["weight_enumerator"]),
        "fingerprint": fingerprint,
    }


def generate_random_candidate(
    rng: np.random.Generator,
    lengths: tuple[int, ...],
    explicit_g: bool,
) -> tuple[tuple[int, ...], tuple[int, ...] | None, int]:
    length = int(rng.choice(lengths))
    h = np.zeros(length, dtype=np.uint8)
    h[0] = 1
    h[-1] = 1
    if length > 2:
        h[1:-1] = rng.integers(0, 2, size=length - 2).astype(np.uint8)
    g: tuple[int, ...] | None = None
    if explicit_g:
        g_arr = np.zeros(length, dtype=np.uint8)
        g_arr[0] = rng.integers(0, 2)
        g_arr[-1] = rng.integers(0, 2)
        if length > 2:
            g_arr[1:-1] = rng.integers(0, 2, size=length - 2).astype(np.uint8)
        g = tuple(int(v) for v in g_arr)
    shift = int(rng.integers(0, 16))
    return tuple(int(v) for v in h), g, shift


def mutate(
    rng: np.random.Generator,
    h: tuple[int, ...],
    g: tuple[int, ...] | None,
    shift: int,
    explicit_g: bool,
) -> list[tuple[tuple[int, ...], tuple[int, ...] | None, int]]:
    moves: list[tuple[tuple[int, ...], tuple[int, ...] | None, int]] = []

    for _ in range(5):
        flipped_h = list(h)
        idx = int(rng.integers(len(flipped_h)))
        flipped_h[idx] ^= 1
        moves.append((tuple(flipped_h), g, shift))

    if explicit_g and g is not None:
        for _ in range(3):
            flipped_g = list(g)
            idx = int(rng.integers(len(flipped_g)))
            flipped_g[idx] ^= 1
            moves.append((h, tuple(flipped_g), shift))

    new_shift = int(rng.integers(0, 16))
    if new_shift != shift:
        moves.append((h, g, new_shift))

    return moves


def search(
    seed: int,
    time_limit_sec: float,
    lengths: tuple[int, ...],
    explicit_g: bool,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    start = time.perf_counter()
    evaluations = 0
    restarts = 0

    best: dict[str, Any] | None = None
    seen: set[str] = set()

    def evaluate(h, g, shift):
        nonlocal evaluations
        evaluations += 1
        result = score(h, g, shift)
        if result is None:
            return None
        fp = result["fingerprint"]
        if fp not in seen:
            seen.add(fp)
            return result
        return None

    while time.perf_counter() - start < time_limit_sec:
        h, g, shift = generate_random_candidate(rng, lengths, explicit_g)
        restarts += 1

        current = evaluate(h, g, shift)
        if current is None:
            continue

        stall = 0
        max_stall = 50

        while stall < max_stall and time.perf_counter() - start < time_limit_sec:
            improved = False
            for cand_h, cand_g, cand_shift in mutate(rng, h, g, shift, explicit_g):
                candidate = evaluate(cand_h, cand_g, cand_shift)
                if candidate is None:
                    continue

                is_better = (
                    candidate["d_min"] > current["d_min"]
                    or (
                        candidate["d_min"] == current["d_min"]
                        and candidate["A_dmin"] < current["A_dmin"]
                    )
                )

                if is_better:
                    h, g, shift = cand_h, cand_g, cand_shift
                    current = candidate
                    improved = True
                    stall = 0
                    break
                else:
                    stall += 1

            if not improved:
                stall += 1

        if best is None or (
            current["d_min"] > best["d_min"]
            or (
                current["d_min"] == best["d_min"]
                and current["A_dmin"] < best["A_dmin"]
            )
        ):
            best = current.copy()
            best["evaluations"] = evaluations
            best["restarts"] = restarts
            best["elapsed_sec"] = time.perf_counter() - start

            improvement = ""
            if current["d_min"] > BASELINE_D_MIN:
                improvement = f" ** NEW d_min={current['d_min']} > {BASELINE_D_MIN}"
            elif (
                current["d_min"] == BASELINE_D_MIN
                and current["A_dmin"] < BASELINE_A_D
            ):
                pct = (1 - current["A_dmin"] / BASELINE_A_D) * 100
                improvement = f" ** {pct:.1f}% fewer A_dmin"

            log(
                f"best: d={current['d_min']} A={current['A_dmin']} "
                f"eval={evaluations} {improvement}"
            )

    if best is not None:
        best["evaluations"] = evaluations
        best["restarts"] = restarts
        best["elapsed_sec"] = time.perf_counter() - start

    return best or {"status": "not_found", "evaluations": evaluations}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--lengths", type=str, default="10,12,14,16")
    parser.add_argument("--explicit-g", action="store_true")
    args = parser.parse_args()

    lengths = tuple(int(v) for v in args.lengths.split(","))

    result = search(
        seed=args.seed,
        time_limit_sec=args.time_limit,
        lengths=lengths,
        explicit_g=args.explicit_g,
    )

    if result is None:
        print("No candidates found")
        return

    result["baseline_fingerprint"] = BASELINE_FINGERPRINT
    result["baseline_d_min"] = BASELINE_D_MIN
    result["baseline_A_dmin"] = BASELINE_A_D

    fingerprint = result.get("fingerprint", "unknown")
    d_min = result.get("d_min", 0)
    a_dmin = result.get("A_dmin", 0)

    is_new_best = (
        d_min > BASELINE_D_MIN
        or (d_min == BASELINE_D_MIN and a_dmin < BASELINE_A_D)
    )

    if is_new_best:
        result["decision"] = "new_best"
        log(f"NEW BEST: d_min={d_min}, A_dmin={a_dmin}")
    else:
        result["decision"] = "not_improving"
        log(f"not improving: d_min={d_min}, A_dmin={a_dmin}")

    print(json.dumps(result, indent=2, ensure_ascii=False, default=list))

    path = save_json("wavelet_32_16_best.json", result)
    log(f"saved: {path}")


if __name__ == "__main__":
    main()
