"""Построение code_metadata.json для экспортируемого experiment package.

Обогащает метаданные Goppa-кодов доказанными характеристиками
зафиксированных пресетов (``goppa.presets``), но только когда
параметры кода (m/degree/seed) точно совпадают с пресетом — иначе
никаких дополнительных значений не придумывается.
"""

from __future__ import annotations

from typing import Any

from goppa.derived import GoppaDerivedCode
from goppa.presets import GOPPA_16_8_CODE, GOPPA_32_16_CODE, GOPPA_64_32_CODE


_GOPPA_PRESETS_BY_NK: dict[tuple[int, int], GoppaDerivedCode] = {
    (16, 8): GOPPA_16_8_CODE,
    (32, 16): GOPPA_32_16_CODE,
    (64, 32): GOPPA_64_32_CODE,
}

_WAVELET_FIELDS = ("h", "g", "a", "b", "shift")
_BCH_FIELDS = (
    "bch_m",
    "bch_designed_distance",
    "bch_primitive_polynomial",
    "bch_first_root",
    "bch_shortening_count",
    "bch_puncture_count",
    "bch_puncture_coordinates",
)
_GOPPA_FIELDS = ("goppa_m", "goppa_degree", "goppa_support_size", "goppa_seed")
_REED_SOLOMON_FIELDS = (
    "reed_solomon_m", "reed_solomon_symbol_n", "reed_solomon_symbol_k",
    "reed_solomon_primitive_polynomial", "reed_solomon_evaluation_points",
    "reed_solomon_column_multipliers",
)
_COMMON_DISTANCE_FIELDS = (
    "minimum_distance_exact",
    "minimum_distance_lower_bound",
    "minimum_distance_upper_bound",
    "distance_evidence",
    "verified_error_correction_radius",
)


def _lookup_goppa_preset(
    n: Any, k: Any, m: Any, degree: Any, seed: Any
) -> GoppaDerivedCode | None:
    """Возвращает зафиксированный пресет, если параметры точно совпадают."""
    if m is None or degree is None:
        return None
    if not isinstance(n, int) or not isinstance(k, int):
        return None

    preset = _GOPPA_PRESETS_BY_NK.get((n, k))
    if preset is None:
        return None

    construction = preset.parent_code.construction
    if construction.m != m or construction.degree != degree:
        return None
    if seed is not None and construction.seed != seed:
        return None

    return preset


def build_code_metadata_list(codes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Строит code_metadata.json из списка код-конфигов (как в
    runtime_config.json / синтетическом config импортированного CSV).

    Ничего не придумывает: значения берутся либо из самого config,
    либо из зафиксированных Goppa-пресетов при точном совпадении
    параметров конструкции.
    """
    result: list[dict[str, Any]] = []

    for code in codes:
        name = code.get("name")
        family = code.get("family")
        n = code.get("n")
        k = code.get("k")

        entry: dict[str, Any] = {
            "name": name,
            "family": family,
            "n": n,
            "k": k,
            "rate": (
                k / n
                if isinstance(n, (int, float))
                and isinstance(k, (int, float))
                and n
                else None
            ),
        }

        if family == "wavelet":
            for field in _WAVELET_FIELDS:
                if field in code:
                    entry[field] = code.get(field)
        elif family in ("bch", "bch_derived"):
            for field in _BCH_FIELDS:
                if field in code:
                    entry[field] = code.get(field)
        elif family == "goppa_derived":
            for field in _GOPPA_FIELDS:
                if field in code:
                    entry[field] = code.get(field)

            preset = _lookup_goppa_preset(
                n,
                k,
                code.get("goppa_m"),
                code.get("goppa_degree"),
                code.get("goppa_seed"),
            )
            if preset is not None:
                entry["parent_k"] = preset.parent_code.k
                entry["distance_lower_bound"] = preset.parent_code.distance_lower_bound
                entry["goppa_polynomial"] = list(
                    preset.parent_code.construction.goppa_polynomial
                )
                entry["construction_seed"] = preset.parent_code.construction.seed

        for field in _COMMON_DISTANCE_FIELDS:
            if field in code and code.get(field) not in (None, ""):
                entry[field] = code.get(field)

        if family == "reed_solomon_binary":
            for field in _REED_SOLOMON_FIELDS:
                if field in code:
                    entry[field] = code.get(field)
        result.append(entry)

    return result
