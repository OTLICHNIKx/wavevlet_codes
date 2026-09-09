"""Финализация кандидатов Wavelet (64,32): строгие сертификаты
w=4 (d>=9) и попытка w=5 (d>=11), углублённая верхняя оценка
(exhaustive message weight <=5 + крупные случайные веса), отпечатки.

Запуск:
    python -m research.optimization.finalize_wavelet_candidates
"""

from __future__ import annotations

import itertools
import json
import time
from typing import Any

import numpy as np

from bch import gf2_matrix_rank
from ldpc import minimum_distance_certificate
from wavelet import WaveletCode

from research.optimization.common import (
    code_fingerprint,
    log,
    save_json,
)

BASELINE_FINGERPRINT = "414d12b0160e51f9"

CANDIDATES: dict[str, dict[str, Any]] = {
    "cand1_len16_shift5": {
        "h": (1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1),
        "shift": 5,
    },
    "cand2_len20_shift18": {
        "h": (1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1),
        "shift": 18,
    },
}


def deep_upper_bound(generator: np.ndarray, seed: int = 5) -> tuple[int, Any]:
    k, n = generator.shape
    row_masks = np.array(
        [int("".join(map(str, row[::-1])), 2) for row in generator],
        dtype=object,
    )
    best = n + 1
    best_source = None
    for weight in range(1, 6):
        for comb in itertools.combinations(range(k), weight):
            value = 0
            for index in comb:
                value ^= row_masks[index]
            word_weight = int(value).bit_count()
            if 0 < word_weight < best:
                best = word_weight
                best_source = ("exhaustive", comb)
    rng = np.random.default_rng(seed)
    generator_int = generator.astype(np.int64)
    for weight in range(6, 28):
        for _ in range(40):
            messages = np.zeros((500, k), dtype=np.int64)
            for row in range(500):
                messages[row, rng.choice(k, size=weight, replace=False)] = 1
            codewords = (messages @ generator_int) % 2
            weights = codewords.sum(axis=1)
            index = int(np.argmin(weights))
            if 0 < weights[index] < best:
                best = int(weights[index])
                best_source = ("random", weight)
    return int(best), best_source


def main() -> None:
    report: dict[str, Any] = {}
    for tag, parameters in CANDIDATES.items():
        code = WaveletCode.from_scaling_coefficients(
            h=parameters["h"],
            g=None,
            codeword_length=64,
            field=2,
            a=1,
            b=1,
            shift=parameters["shift"],
            name="wavelet_64_32_finalist",
        )
        generator = code.generator_matrix
        parity_check = code.parity_check_matrix
        fingerprint = code_fingerprint(generator)
        entry: dict[str, Any] = {
            "parameters": {
                "h": list(parameters["h"]),
                "shift": parameters["shift"],
                "a": 1,
                "b": 1,
                "g": None,
            },
            "rank_G": int(gf2_matrix_rank(generator)),
            "rank_H": int(gf2_matrix_rank(parity_check)),
            "orthogonality_ok": bool(
                np.all(
                    (
                        generator.astype(np.int64)
                        @ parity_check.astype(np.int64).T
                    )
                    % 2
                    == 0
                )
            ),
            "fingerprint": fingerprint,
            "differs_from_baseline": fingerprint != BASELINE_FINGERPRINT,
        }
        for w in (4, 5):
            start = time.perf_counter()
            bound = minimum_distance_certificate(parity_check, w)
            entry[f"certificate_w{w}"] = {
                "guaranteed_d_min_lower_bound": int(bound),
                "runtime_sec": round(time.perf_counter() - start, 2),
            }
            log(f"{tag}: cert w={w} -> d>={bound} ({entry[f'certificate_w{w}']['runtime_sec']}s)")
        start = time.perf_counter()
        upper, source = deep_upper_bound(generator)
        entry["upper_bound"] = {
            "found_word_weight": upper,
            "source_message": repr(source),
            "runtime_sec": round(time.perf_counter() - start, 1),
        }
        log(f"{tag}: deep upper bound d <= {upper}")
        report[tag] = entry

    save_json("wavelet_64_32_finalists.json", report)
    log("saved wavelet_64_32_finalists.json")


if __name__ == "__main__":
    main()
