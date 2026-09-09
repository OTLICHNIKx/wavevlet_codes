"""Этап B: офлайн-поиск Wavelet (64,32) с строго доказанным d_min >= 9.

Переменные поиска (в рамках существующей реализации
``WaveletCode.from_scaling_coefficients``, a=b=1, g авто=reverse(h)):
  * h  — бинарный фильтр чётной длины L (первый/последний = 1);
  * shift — параметр матрицы сдвига J.

Двухстадийный скоринг через нарушения строгого синдромного
сертификата (ViolationScorer):
  * стадия 1: w=3 (зависимости веса <= 6)  -> спуск к 0 => d_min >= 7;
  * стадия 2: w=4 (зависимости веса <= 8)  -> спуск к 0 => d_min >= 9.

Финальный кандидат проходит независимо ``ldpc.minimum_distance_
certificate(H_C, 4)`` (тот же математический критерий, но отдельная
реализация) и поиск верхнего слова (этап Stage 4 по ТЗ).

Запуск:
    python -m research.optimization.optimize_wavelet_64_32 --time-limit 3600
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

import numpy as np

from ldpc import minimum_distance_certificate
from wavelet import WaveletCode

from research.optimization.common import (
    ViolationScorer,
    code_fingerprint,
    log,
    upper_bound_low_weight_search,
)

BASELINE_FINGERPRINT = "414d12b0160e51f9"  # wavelet_64_32 из baseline.json


def build_wavelet(
    h: tuple[int, ...],
    shift: int,
) -> WaveletCode | None:
    try:
        return WaveletCode.from_scaling_coefficients(
            h=h,
            g=None,
            codeword_length=64,
            field=2,
            a=1,
            b=1,
            shift=shift,
            name="wavelet_64_32_candidate",
        )
    except ValueError:
        return None


def candidate_state(
    rng: np.random.Generator,
    lengths: tuple[int, ...],
) -> tuple[tuple[int, ...], int]:
    while True:
        length = int(rng.choice(lengths))
        h = np.zeros(length, dtype=np.uint8)
        h[0] = 1
        h[-1] = 1
        if length > 2:
            inner = rng.integers(0, 2, size=length - 2).astype(np.uint8)
            h[1:-1] = inner
        shift = int(rng.integers(1, 32))
        code = build_wavelet(tuple(int(v) for v in h), shift)
        if code is not None:
            return tuple(int(v) for v in h), shift


def try_moves(
    rng: np.random.Generator,
    h: tuple[int, ...],
    shift: int,
    max_row_weight: None,
) -> list[tuple[tuple[int, ...], int]]:
    moves: list[tuple[tuple[int, ...], int]] = []
    for _ in range(3):
        flipped = list(h)
        index = int(rng.integers(len(flipped)))
        flipped[index] ^= 1
        moves.append((tuple(flipped), shift))
    moves.append((h, int(rng.integers(1, 32))))
    if len(h) > 4:
        swapped = list(h)
        i = int(rng.integers(len(swapped)))
        j = int(rng.integers(len(swapped)))
        swapped[i], swapped[j] = swapped[j], swapped[i]
        moves.append((tuple(swapped), shift))
    return moves


def search(
    seed: int,
    time_limit_sec: float,
    lengths: tuple[int, ...],
    stall_limit: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    scorer6 = ViolationScorer(64, 3)
    scorer8 = ViolationScorer(64, 4)
    start = time.perf_counter()
    evaluations = 0
    restarts = 0
    best: dict[str, Any] | None = None

    def evaluate(h, shift, scorer):
        nonlocal evaluations
        evaluations += 1
        code = build_wavelet(h, shift)
        if code is None:
            return None, None
        violations, columns = scorer.violations(code.parity_check_matrix)
        return violations, (columns, code)

    # грубая разведка: несколько рестартов на стадии 1
    while time.perf_counter() - start < time_limit_sec:
        h, shift = candidate_state(rng, lengths)
        restarts += 1
        v6, packed = evaluate(h, shift, scorer6)
        if v6 is None:
            continue
        columns = packed[0]
        stall = 0
        while v6 > 0 and stall < stall_limit and time.perf_counter() - start < time_limit_sec:
            progressed = False
            for candidate_h, candidate_shift in try_moves(
                rng, h, shift, None
            ):
                candidate_v6, candidate_packed = evaluate(
                    candidate_h, candidate_shift, scorer6
                )
                if candidate_v6 is None:
                    continue
                if candidate_v6 <= v6:
                    h, shift, v6, columns = (
                        candidate_h,
                        candidate_shift,
                        candidate_v6,
                        candidate_packed[0],
                    )
                    progressed = True
                    stall = stall if candidate_v6 == v6 else 0
                    if candidate_v6 < v6:
                        stall = 0
                    break
            if not progressed:
                stall += 1
        if best is None or v6 < best["stage1_violations"]:
            best = {
                "h": h,
                "shift": shift,
                "stage1_violations": v6,
                "evaluations": evaluations,
                "restarts": restarts,
            }
            log(f"stage1 best violations={v6} h={h} shift={shift}")
        if v6 > 0:
            continue
        # стадия 2: d >= 9 (нарушения сертификата w=4)
        v8, packed8 = evaluate(h, shift, scorer8)
        columns8 = packed8[0]
        code8 = packed8[1]
        stall = 0
        while v8 > 0 and stall < 800 and time.perf_counter() - start < time_limit_sec:
            progressed = False
            for candidate_h, candidate_shift in try_moves(
                rng, h, shift, None
            ):
                candidate_code = build_wavelet(candidate_h, candidate_shift)
                if candidate_code is None:
                    continue
                evaluations += 1
                # быстрая проверка: стадия 1 не должна сломаться
                candidate_v6, _ = evaluate(
                    candidate_h, candidate_shift, scorer6
                )
                if candidate_v6 is None or candidate_v6 > 0:
                    continue
                candidate_v8, candidate_columns8 = scorer8.violations(
                    candidate_code.parity_check_matrix
                )
                evaluations += 1
                if candidate_v8 <= v8:
                    h, shift, v8, columns8 = (
                        candidate_h,
                        candidate_shift,
                        candidate_v8,
                        candidate_columns8,
                    )
                    progressed = True
                    stall = 0 if candidate_v8 < v8 else stall + 1
                    break
            if not progressed:
                stall += 20
        if best is not None and v8 < best.get("stage2_violations", 10 ** 9):
            best.update({"stage2_violations": v8, "h": h, "shift": shift})
            log(f"stage2 best violations={v8} h={h} shift={shift}")
        if v8 == 0:
            code = build_wavelet(h, shift)
            if code is None:
                continue
            certified = (
                minimum_distance_certificate(
                    code.parity_check_matrix, 4
                )
                == 9
            )
            if certified:
                fingerprint = code_fingerprint(code.generator_matrix)
                upper, positions = upper_bound_low_weight_search(
                    code.generator_matrix,
                    exhaustive_message_weight=3,
                    random_weights=range(4, 17),
                    samples_per_weight=50_000,
                    seed=seed,
                )
                return {
                    "status": "found",
                    "h": h,
                    "shift": shift,
                    "a": 1,
                    "b": 1,
                    "g": None,
                    "fingerprint": fingerprint,
                    "differs_from_baseline": fingerprint
                    != BASELINE_FINGERPRINT,
                    "certificate_w4": int(
                        minimum_distance_certificate(
                            code.parity_check_matrix, 4
                        )
                    ),
                    "upper_bound_word_weight": int(upper),
                    "upper_bound_message": list(positions),
                    "evaluations": evaluations,
                    "restarts": restarts,
                    "elapsed_sec": time.perf_counter() - start,
                }
    return {
        "status": "not_found",
        "best": best,
        "evaluations": evaluations,
        "restarts": restarts,
        "elapsed_sec": time.perf_counter() - start,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260909)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--lengths", type=str, default="16,24,32")
    parser.add_argument("--stall-limit", type=int, default=1500)
    args = parser.parse_args()

    lengths = tuple(int(value) for value in args.lengths.split(","))
    result = search(
        seed=args.seed,
        time_limit_sec=args.time_limit,
        lengths=lengths,
        stall_limit=args.stall_limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    from research.optimization.common import save_json

    path = save_json("wavelet_64_32_best.json", result)
    log(f"saved: {path}")


if __name__ == "__main__":
    main()
