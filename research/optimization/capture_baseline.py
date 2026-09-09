"""Этап A: фиксация baseline до любых изменений пресетов.

Строит РЕАЛЬНЫЕ коды, участвующие в текущем four/five-family
сравнении (final configs, включая поздние replace-override), и
сохраняет матрицы, отпечатки, параметры конструкции, точные
расстояния для k <= 16 и строгие сертификаты/верхние оценки для
(64,32).

Запуск:
    python -m research.optimization.capture_baseline
"""

from __future__ import annotations

from typing import Any

import numpy as np

from research.config import (
    FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
    FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
    FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
)
from research.code_factory import build_code_from_config

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    log,
    matrices_valid,
    save_json,
    upper_bound_low_weight_search,
)
from ldpc import minimum_distance_certificate


PARAM_FIELDS = (
    "family",
    "h",
    "g",
    "a",
    "b",
    "shift",
    "bch_m",
    "bch_designed_distance",
    "bch_first_root",
    "bch_shortening_count",
    "bch_puncture_count",
    "bch_puncture_coordinates",
    "goppa_m",
    "goppa_degree",
    "goppa_support_size",
    "goppa_seed",
    "reed_solomon_m",
    "reed_solomon_symbol_n",
    "reed_solomon_symbol_k",
    "reed_solomon_primitive_polynomial",
    "reed_solomon_evaluation_points",
    "reed_solomon_column_multipliers",
    "minimum_distance_exact",
    "minimum_distance_lower_bound",
    "minimum_distance_upper_bound",
    "distance_evidence",
    "verified_error_correction_radius",
)


def capture_code(code_config) -> dict[str, Any]:
    code = build_code_from_config(code_config)
    generator = np.asarray(code.generator_matrix, dtype=np.uint8)
    parity_check = np.asarray(code.parity_check_matrix, dtype=np.uint8)

    entry: dict[str, Any] = {
        "name": code_config.name,
        "family": code_config.family,
        "n": int(code.n),
        "k": int(code.k),
        "rate": code.k / code.n,
        "shapes_ok": generator.shape == (code.k, code.n),
        "rank_G": int(_rank(generator)),
        "rank_H": int(_rank(parity_check)),
        "orthogonality_ok": bool(np.all(
            (generator.astype(np.int64) @ parity_check.astype(np.int64).T) % 2 == 0
        )),
        "matrices_valid": matrices_valid(
            generator, parity_check, code.n, code.k
        ),
        "fingerprint_rref_G": code_fingerprint(generator),
        "fingerprint_rref_H": code_fingerprint(parity_check),
        "generator_hex_rows": _hex_rows(generator),
        "parity_check_hex_rows": _hex_rows(parity_check),
        "parameters": {
            field: getattr(code_config, field)
            for field in PARAM_FIELDS
        },
    }

    if code.k <= 16:
        analysis = exact_weight_enumerator(generator)
        entry["distance_exact_enum"] = {
            "d_min_exact": analysis["d_min_exact"],
            "A_dmin": analysis["A_dmin"],
            "weight_enumerator": list(analysis["weight_enumerator"]),
        }
    else:
        upper, positions = upper_bound_low_weight_search(generator)
        entry["distance_upper_bound_found_weight"] = upper
        entry["distance_upper_example_message"] = list(positions)
        entry["distance_certificates"] = {
            f"w={w} -> d>={2 * w + 1}": bool(
                minimum_distance_certificate(parity_check, w) == 2 * w + 1
            )
            for w in (2, 3, 4)
        }

    return entry


def _rank(matrix: np.ndarray) -> int:
    from bch import gf2_matrix_rank

    return gf2_matrix_rank(matrix)


def _rref_rows(matrix: np.ndarray) -> np.ndarray:
    return matrix


def _hex_rows(matrix: np.ndarray) -> list[str]:
    from ldpc import matrix_to_hex_rows

    return list(matrix_to_hex_rows(matrix))


def main() -> None:
    baseline: dict[str, Any] = {}
    for config in (
        FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
        FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
        FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
    ):
        size = config.codes[0].n
        log(f"baseline for size ({size}, {size // 2})")
        baseline[f"{size}_{size // 2}"] = [
            capture_code(code_config) for code_config in config.codes
        ]

    path = save_json("baseline.json", baseline)
    log(f"saved: {path}")
    for size_key, entries in baseline.items():
        for entry in entries:
            exact = entry.get("distance_exact_enum", {}).get("d_min_exact")
            bound = entry.get("distance_upper_bound_found_weight")
            certs = entry.get("distance_certificates", {})
            proven = max(
                (int(key.split(">=")[1])
                 for key, ok in certs.items() if ok),
                default=None,
            )
            log(
                f"  {entry['family']:<20} n={entry['n']} "
                f"exact={exact if exact is not None else '-'} "
                f"cert_lower={proven if proven else '-'} "
                f"upper_found={bound if bound else '-'} "
                f"fp={entry['fingerprint_rref_G']}"
            )


if __name__ == "__main__":
    main()
