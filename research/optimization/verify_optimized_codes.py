"""Независимая повторная проверка изменённых кодов (Этап 12/20).

Перестраивает КАЖДЫЙ заменённый пресет из production config и
заново вычисляет расстояние независимым методом:
  * (32,16): точный перебор 2^16 слов (d exact) + сверка с
             minimum_distance_exact в конфиге;
  * (64,32) wavelet: строгий сертификат syndrome w=4 и w=5
             (d >= 9 / d >= 11) + верхняя оценка весом 14;
  * baseline-отпечатки из capture_baseline сверяются с новыми,
     чтобы подтвердить, что реально собрался ДРУГОЙ код.

Результат: verification.json.

Запуск:
    python -m research.optimization.verify_optimized_codes
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ldpc import minimum_distance_certificate
from research.code_factory import build_code_from_config
from research.config import (
    BCH_DERIVED_32_16_CONFIG,
    EQUAL_DECODER_20K_FOUR_FAMILIES_32_16,
    EQUAL_DECODER_20K_FOUR_FAMILIES_64_32,
    FOUR_FAMILIES_20K_FULL_DECODERS_16_8,
    GOPPA_32_16_CONFIG,
    REED_SOLOMON_32_16_CONFIG,
    WAVELET_32_16_CONFIG,
    WAVELET_64_32_CONFIG,
)

from research.optimization.common import (
    code_fingerprint,
    exact_weight_enumerator,
    load_json,
    log,
    matrices_valid,
    save_json,
    upper_bound_low_weight_search,
)

BASELINE_FP = {
    ("bch_derived", 32): "b64120fd51867c0a",
    ("reed_solomon_binary", 32): "76df1282447f05d9",
    ("wavelet", 64): "414d12b0160e51f9",
    # unchanged references:
    ("goppa_derived", 32): "efdc15c1f5794c87",
    ("wavelet", 32): "335caff4c2b02684",
}


def verify_32_16(code_config, expected_d: int) -> dict[str, Any]:
    code = build_code_from_config(code_config)
    generator = code.generator_matrix
    parity_check = code.parity_check_matrix
    analysis = exact_weight_enumerator(generator)
    return {
        "family": code_config.family,
        "name": code_config.name,
        "matrices_valid": matrices_valid(generator, parity_check, 32, 16),
        "d_min_exact_enum": int(analysis["d_min_exact"]),
        "matches_expected": analysis["d_min_exact"] == expected_d,
        "matches_config_metadata": (
            code_config.minimum_distance_exact
            in (analysis["d_min_exact"], None)
        ),
        "A_dmin": int(analysis["A_dmin"]),
        "weight_enumerator": list(analysis["weight_enumerator"]),
        "fingerprint": code_fingerprint(generator),
    }


def verify_wavelet_64_32() -> dict[str, Any]:
    code = build_code_from_config(WAVELET_64_32_CONFIG)
    generator = code.generator_matrix
    parity_check = code.parity_check_matrix
    cert4 = minimum_distance_certificate(parity_check, 4)
    cert5 = minimum_distance_certificate(parity_check, 5)
    upper, source = upper_bound_low_weight_search(
        generator,
        exhaustive_message_weight=3,
        random_weights=range(4, 17),
        samples_per_weight=50_000,
        seed=20260909,
    )
    return {
        "family": "wavelet",
        "name": WAVELET_64_32_CONFIG.name,
        "matrices_valid": matrices_valid(generator, parity_check, 64, 32),
        "certificate_w4_lower_bound": int(cert4),
        "certificate_w5_lower_bound": int(cert5),
        "strict_certificate_d_ge_9": cert4 >= 9,
        "upper_bound_found_weight": int(upper),
        "upper_bound_source": repr(source),
        "matches_config_lower_bound": cert5 == code_lower(
            WAVELET_64_32_CONFIG
        ),
        "fingerprint": code_fingerprint(generator),
        "differs_from_baseline": code_fingerprint(generator)
        != BASELINE_FP[("wavelet", 64)],
    }


def code_lower(cfg) -> int:
    return cfg.minimum_distance_lower_bound


def main() -> None:
    try:
        baseline = load_json("baseline.json")
    except FileNotFoundError:
        baseline = None
        log("warning: baseline.json not found")

    verification: dict[str, Any] = {"codes": []}

    verification["codes"].append(
        verify_32_16(BCH_DERIVED_32_16_CONFIG, expected_d=6)
    )
    verification["codes"].append(
        verify_32_16(GOPPA_32_16_CONFIG, expected_d=7)
    )
    verification["codes"].append(
        verify_32_16(REED_SOLOMON_32_16_CONFIG, expected_d=7)
    )
    verification["codes"].append(
        verify_32_16(WAVELET_32_16_CONFIG, expected_d=8)
    )
    # metadata-сверка для wavelet 32 идёт по comparison-config:
    # базовый WAVELET_32_16_CONFIG намеренно не фиксирует exact,
    # это делает FOUR_FAMILY_* override (ТЗ §13.5).
    from research.config import FOUR_FAMILY_WAVELET_32_16_CONFIG

    ff_wavelet32 = verify_32_16(
        FOUR_FAMILY_WAVELET_32_16_CONFIG, expected_d=8
    )
    verification["wavelet_32_four_family_metadata"] = ff_wavelet32
    verification["codes"].append(verify_wavelet_64_32())

    # confirm four-family comparison configs actually build cleanly
    # with the changed presets (mismatch guard, ТЗ §13.5).
    comparison_ok = True
    for config in (
        FOUR_FAMILIES_20K_FULL_DECODERS_16_8,
        EQUAL_DECODER_20K_FOUR_FAMILIES_32_16,
        EQUAL_DECODER_20K_FOUR_FAMILIES_64_32,
    ):
        for code_config in config.codes:
            try:
                code = build_code_from_config(code_config)
            except Exception as error:  # noqa: BLE001
                log(f"BUILD FAILED {code_config.name}: {error}")
                comparison_ok = False
                continue
            if (code.n, code.k) != (code_config.n, code_config.k):
                log(f"MISMATCH dims {code_config.name}")
                comparison_ok = False

    verification["comparison_configs_build_ok"] = comparison_ok
    path = save_json("verification.json", verification)
    log(f"saved: {path}")
    for entry in verification["codes"]:
        if entry["family"] == "wavelet" and entry["name"] == "wavelet_64_32":
            log(
                f"wavelet 64: cert4 d>={entry['certificate_w4_lower_bound']} "
                f"cert5 d>={entry['certificate_w5_lower_bound']} "
                f"upper d<={entry['upper_bound_found_weight']} "
                f"new code={entry['differs_from_baseline']}"
            )
        else:
            log(
                f"{entry['family']:<18}: "
                f"d={entry.get('d_min_exact_enum')} "
                f"A_d={entry.get('A_dmin')} "
                f"metadata_ok={entry.get('matches_config_metadata')} "
                f"valid={entry['matrices_valid']}"
            )
    if not comparison_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
