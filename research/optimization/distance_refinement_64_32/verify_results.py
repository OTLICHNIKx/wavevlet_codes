"""Проверка результатов уточнения БЕЗ повторного MITM-поиска.

Строит коды из production, сверяет fingerprint с сохранёнными,
перепроверяет:
  * сертификат subsets <=4 (d >= 9) — быстро, ~секунды;
  * заявленное минимальное слово: принадлежит коду (m·G), нулевой
    синдром, точный вес;
  * статусы exact/lower bound соответствуют сохранённым данным.

Запуск:
    python -m research.optimization.distance_refinement_64_32.verify_results
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

from research.config import (
    BCH_DERIVED_64_32_CONFIG,
    LDPC_64_32_CONFIG,
)
from research.code_factory import build_code_from_config
from ldpc.presets import LDPC_64_32

from research.optimization.distance_refinement_64_32.syndrome_search import (
    refine_certificate,
)

RESULTS_DIR = pathlib.Path("research_results/distance_refinement_64_32")


def check_entry(name: str, code, entry: dict, errors: list[str]) -> dict:
    from research.optimization.common import (
        code_fingerprint,
        matrices_valid,
    )

    report: dict = {"family": name}
    generator = np.asarray(code.generator_matrix, dtype=np.uint8)
    parity_check = np.asarray(code.parity_check_matrix, dtype=np.uint8)
    fingerprint = code_fingerprint(generator)
    report["fingerprint"] = fingerprint
    if fingerprint != entry.get("baseline_fingerprint"):
        errors.append(f"{name}: fingerprint рассогласован")
    if not matrices_valid(generator, parity_check, code.n, code.k):
        errors.append(f"{name}: матрицы невалидны")
    certificate = refine_certificate(parity_check, 4)
    report["certificate_d_ge_9"] = bool(certificate["clean"])
    if not certificate["clean"]:
        errors.append(f"{name}: сертификат d>=9 не проходит")
    status = entry.get("status")
    report["status"] = status
    if status == "exact":
        support = entry["min_support"]
        weight = entry["d_min_exact"]
        word = np.zeros(code.n, dtype=np.uint8)
        word[support] = 1
        syndrome = (parity_check.astype(np.int64) @ word) % 2
        ok = (
            int(word.sum()) == weight
            and bool(np.all(syndrome == 0))
        )
        message = np.asarray(entry["min_message"], dtype=np.uint8)
        if not np.array_equal((message @ generator) % 2, word):
            ok = False
        report["min_word_verified"] = bool(ok)
        report["min_word_weight"] = weight
        report["A_dmin_recorded"] = entry.get("A_dmin")
        if not ok:
            errors.append(f"{name}: минимальное слово не сходится")
    elif status == "lower_bound_only":
        report["d_min_lower_bound"] = entry.get("d_min_lower_bound")
        report["cleared_weights"] = entry.get("cleared_weights")
        report["upper_bound_recorded"] = entry.get("upper_bound")
    else:
        errors.append(f"{name}: неизвестный статус {status}")
    return report


def main() -> None:
    results_path = RESULTS_DIR / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    reports: list[dict] = []

    bch_code = build_code_from_config(BCH_DERIVED_64_32_CONFIG)
    if "bch_derived_64_32" in results:
        reports.append(
            check_entry(
                "bch_derived_64_32", bch_code,
                results["bch_derived_64_32"], errors,
            )
        )
    if "ldpc_64_32" in results:
        reports.append(
            check_entry("ldpc_64_32", LDPC_64_32, results["ldpc_64_32"], errors)
        )

    payload = {
        "all_ok": not errors,
        "errors": errors,
        "reports": reports,
        "note": (
            "fingerprint + certificate d>=9 + точная проверка "
            "заявленного минимального слова (m·G, вес, синдром)"
        ),
    }
    (RESULTS_DIR / "verify_results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:1800])
    if errors:
        print("VERIFY FAILED")
        sys.exit(1)
    print("verification passed")


if __name__ == "__main__":
    main()
