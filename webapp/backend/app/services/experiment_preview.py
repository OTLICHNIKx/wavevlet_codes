"""Backend preview and fairness analysis for a research configuration."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models.config import ResearchConfigSchema
from app.services.config_adapter import schema_to_research, validate_schema
from research.config import CodeResearchConfig, DecoderResearchConfig


def build_experiment_preview(schema: ResearchConfigSchema) -> dict[str, Any]:
    validation = validate_schema(schema)
    if not validation.valid:
        fairness_warnings = _schema_fairness_warnings(schema)
        return {
            "valid": False,
            "errors": validation.errors,
            "warnings": _deduplicate(validation.warnings + fairness_warnings),
            "common_random_numbers": _common_random_numbers_report(),
            "groups": [],
            "workload": validation.report,
        }

    config = schema_to_research(schema)
    warnings = list(validation.warnings)
    groups: list[dict[str, Any]] = []
    codes_by_length: dict[int, list[CodeResearchConfig]] = defaultdict(list)
    for code in config.codes:
        codes_by_length[code.n].append(code)

    for n, codes in sorted(codes_by_length.items()):
        rates = {code.k / code.n for code in codes}
        rate_matched = len(rates) == 1
        if not rate_matched:
            values = ", ".join(
                f"{code.name} [{code.n},{code.k}]: R={code.k / code.n:.3f}"
                for code in codes
            )
            warnings.append(f"WARNING: Rate mismatch: {values}")

        code_reports = [
            _code_report(code, config.decoders, warnings)
            for code in codes
        ]
        parameter_sets = {
            (
                item["syndrome_t"],
                item["chase_inner_t"],
                item["chase_p"],
            )
            for item in code_reports
        }
        decoder_matched = len(parameter_sets) == 1
        if not decoder_matched:
            values = ", ".join(
                f"{item['name']}: syndrome_t={item['syndrome_t']}, "
                f"chase_t={item['chase_inner_t']}, p={item['chase_p']}"
                for item in code_reports
            )
            warnings.append(
                f"WARNING: Decoder parameters are not equal for n={n}: {values}"
            )

        dimensions = {(code.n, code.k) for code in codes}
        groups.append(
            {
                "key": (
                    f"[{n},{codes[0].k}]"
                    if len(dimensions) == 1
                    else f"n={n} (mixed rates)"
                ),
                "n": n,
                "rate_matched": rate_matched,
                "decoder_matched": decoder_matched,
                "codes": code_reports,
            }
        )

    workload = config.estimate_workload()
    workload.update(
        {
            "snr_point_count": len(config.ebn0_db_values),
            "code_snr_points": len(config.codes) * len(config.ebn0_db_values),
            "maximum_decoder_evaluations": workload["total_series"],
            "level": _workload_level(workload["total_frames"]),
        }
    )

    return {
        "valid": True,
        "errors": [],
        "warnings": _deduplicate(warnings),
        "summary": {
            "message_count": config.message_count,
            "ebn0_db_values": list(config.ebn0_db_values),
            "code_count": len(config.codes),
            "family_count": len({code.family for code in config.codes}),
            "families": sorted({code.family for code in config.codes}),
            "message_seed": config.message_seed,
            "noise_seed": config.noise_seed,
        },
        "common_random_numbers": _common_random_numbers_report(),
        "groups": groups,
        "workload": workload,
    }


def _code_report(
    code: CodeResearchConfig,
    decoders: DecoderResearchConfig,
    warnings: list[str],
) -> dict[str, Any]:
    syndrome_t = (
        code.syndrome_max_error_weight
        if code.syndrome_max_error_weight is not None
        else decoders.syndrome_max_error_weight
    )
    chase_t = (
        code.chase_inner_decoder_max_error_weight
        if code.chase_inner_decoder_max_error_weight is not None
        else decoders.chase_inner_decoder_max_error_weight
    )
    chase_p = (
        code.chase_unreliable_positions_count
        if code.chase_unreliable_positions_count is not None
        else decoders.chase_unreliable_positions_count
    )

    known_distance = (
        code.minimum_distance_exact
        if code.minimum_distance_exact is not None
        else code.minimum_distance_lower_bound
    )
    guaranteed_radius = (
        (known_distance - 1) // 2
        if known_distance is not None
        else None
    )
    if (
        decoders.run_syndrome
        and guaranteed_radius is not None
        and syndrome_t > guaranteed_radius
    ):
        warnings.append(
            f"{code.name}: configured syndrome t={syndrome_t} exceeds "
            f"known guaranteed radius {guaranteed_radius}"
        )

    mld_skipped = code.k > decoders.max_k_for_mld
    mld_reason = (
        f"k={code.k} exceeds max_k_for_mld={decoders.max_k_for_mld}"
        if mld_skipped
        else None
    )
    return {
        "name": code.name,
        "family": code.family,
        "n": code.n,
        "k": code.k,
        "rate": code.k / code.n,
        "syndrome_t": syndrome_t,
        "chase_inner_t": chase_t,
        "chase_p": chase_p,
        "guaranteed_radius": guaranteed_radius,
        "hard_mld": _mld_status(decoders.run_hard_mld, mld_skipped, mld_reason),
        "soft_mld": _mld_status(decoders.run_soft_mld, mld_skipped, mld_reason),
    }


def _schema_fairness_warnings(schema: ResearchConfigSchema) -> list[str]:
    warnings: list[str] = []
    by_n: dict[int, list[Any]] = defaultdict(list)
    for code in schema.codes:
        by_n[code.n].append(code)
    for n, codes in by_n.items():
        rates = {code.k / n for code in codes}
        if len(rates) > 1:
            values = ", ".join(
                f"{code.name} [{code.n},{code.k}]: R={code.k / n:.3f}"
                for code in codes
            )
            warnings.append(f"WARNING: Rate mismatch: {values}")
        decoder_values = {
            (
                code.syndrome_max_error_weight,
                code.chase_inner_decoder_max_error_weight,
                code.chase_unreliable_positions_count,
            )
            for code in codes
        }
        if len(decoder_values) > 1:
            warnings.append(
                f"WARNING: Decoder parameters are not equal for n={n}"
            )
    return warnings


def _mld_status(enabled: bool, skipped: bool, reason: str | None) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled", "reason": None}
    if skipped:
        return {"status": "skipped", "reason": reason}
    return {"status": "enabled", "reason": None}


def _common_random_numbers_report() -> dict[str, Any]:
    return {
        "enabled": True,
        "same_information_messages": True,
        "same_base_noise": True,
        "scope": "inside each (n,k) group",
    }


def _workload_level(total_frames: int) -> str:
    if total_frames >= 1_000_000:
        return "high"
    if total_frames >= 100_000:
        return "medium"
    return "low"


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
