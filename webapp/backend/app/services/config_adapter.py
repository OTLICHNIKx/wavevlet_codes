"""Единый адаптер между API-схемой и research dataclass-конфигурацией."""

from dataclasses import fields
from typing import Any

import numpy as np

from decode.syndrome_decoding import recover_message_from_codeword
from app.models.config import ResearchConfigSchema, ValidationResponse
from research.code_factory import build_code_from_config
from research.config import (
    BCH_15_7_CONFIG,
    BCH_63_45_CONFIG,
    BCH_DERIVED_16_8_CONFIG,
    BCH_DERIVED_32_16_CONFIG,
    BCH_DERIVED_64_32_CONFIG,
    COMPARE_16_8_SMOKE_CONFIG,
    COMPARE_32_16_SMOKE_CONFIG,
    COMPARE_64_32_EQUAL_T3_SMOKE_CONFIG,

    EQUAL_DECODER_SMOKE_CONFIG,
    EQUAL_DECODER_20K_CONFIG,

    FINAL_20K_PRESET,
    WAVELET_16_8_CONFIG,
    WAVELET_32_16_CONFIG,
    WAVELET_64_32_CONFIG,
    CodeResearchConfig,
    DecoderResearchConfig,
    ResearchConfig,
)
from wavelet.code import gf_rank


CODE_PRESETS = {
    "WAVELET_16_8_CONFIG": WAVELET_16_8_CONFIG,
    "WAVELET_32_16_CONFIG": WAVELET_32_16_CONFIG,
    "WAVELET_64_32_CONFIG": WAVELET_64_32_CONFIG,
    "BCH_15_7_CONFIG": BCH_15_7_CONFIG,
    "BCH_63_45_CONFIG": BCH_63_45_CONFIG,
    "BCH_DERIVED_16_8_CONFIG": BCH_DERIVED_16_8_CONFIG,
    "BCH_DERIVED_32_16_CONFIG": BCH_DERIVED_32_16_CONFIG,
    "BCH_DERIVED_64_32_CONFIG": BCH_DERIVED_64_32_CONFIG,
}

RESEARCH_PRESETS = {
    "EQUAL_DECODER_SMOKE_CONFIG": EQUAL_DECODER_SMOKE_CONFIG,
    "EQUAL_DECODER_20K_CONFIG": EQUAL_DECODER_20K_CONFIG,

    "COMPARE_64_32_EQUAL_T3_SMOKE_CONFIG": COMPARE_64_32_EQUAL_T3_SMOKE_CONFIG,
    "COMPARE_16_8_SMOKE_CONFIG": COMPARE_16_8_SMOKE_CONFIG,
    "COMPARE_32_16_SMOKE_CONFIG": COMPARE_32_16_SMOKE_CONFIG,

    "FINAL_20K_PRESET": FINAL_20K_PRESET,
}


def _known_fields(cls: type) -> set[str]:
    return {item.name for item in fields(cls)}


def schema_to_research(
    schema: ResearchConfigSchema,
    results_dir: str | None = None,
) -> ResearchConfig:
    data = schema.model_dump()
    code_fields = _known_fields(CodeResearchConfig)
    decoder_fields = _known_fields(DecoderResearchConfig)

    codes = tuple(
        CodeResearchConfig.from_json_dict(
            {key: value for key, value in code.items() if key in code_fields}
        )
        for code in data["codes"]
    )
    decoders = DecoderResearchConfig.from_json_dict(
        {
            key: value
            for key, value in data["decoders"].items()
            if key in decoder_fields
        }
    )

    return ResearchConfig(
        message_count=data["message_count"],
        message_seed=data["message_seed"],
        noise_seed=data["noise_seed"],
        ebn0_db_values=tuple(data["ebn0_db_values"]),
        codes=codes,
        decoders=decoders,
        results_dir=results_dir or data.get("results_dir") or "research_results",
    )


def validate_schema(schema: ResearchConfigSchema) -> ValidationResponse:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        config = schema_to_research(schema)
    except (TypeError, ValueError) as exc:
        return ValidationResponse(valid=False, errors=[str(exc)])

    if len({code.name for code in config.codes}) != len(config.codes):
        errors.append("Имена кодов должны быть уникальными")

    if not any(
        (
            config.decoders.run_syndrome,
            config.decoders.run_hard_mld,
            config.decoders.run_soft_mld,
            config.decoders.run_chase,
        )
    ):
        errors.append("Необходимо включить хотя бы один декодер")

    for code_config in config.codes:
        try:
            code = build_code_from_config(code_config)
            generator = np.asarray(code.generator_matrix, dtype=np.uint8)
            parity_check = np.asarray(code.parity_check_matrix, dtype=np.uint8)

            if gf_rank(generator, 2) != code_config.k:
                raise ValueError("порождающая матрица не имеет полного ранга")
            if gf_rank(parity_check, 2) != code_config.n - code_config.k:
                raise ValueError("проверочная матрица не имеет полного ранга")

            message = np.zeros((1, code_config.k), dtype=np.uint8)
            message[0, 0] = 1
            if code_config.k > 1:
                message[0, -1] = 1

            encoded = (message @ generator) % 2
            if not np.all((encoded @ parity_check.T) % 2 == 0):
                raise ValueError("encode sanity check не пройден")

            restored = recover_message_from_codeword(
                corrected_word=encoded[0],
                generator_matrix=generator,
            )
            if not np.array_equal(restored, message[0]):
                raise ValueError("encode/extract round-trip не пройден")
        except (TypeError, ValueError) as exc:
            errors.append(f"{code_config.name}: {exc}")

        chase_p = (
            code_config.chase_unreliable_positions_count
            if code_config.chase_unreliable_positions_count is not None
            else config.decoders.chase_unreliable_positions_count
        )
        syndrome_t = (
            code_config.syndrome_max_error_weight
            if code_config.syndrome_max_error_weight is not None
            else config.decoders.syndrome_max_error_weight
        )
        chase_t = (
            code_config.chase_inner_decoder_max_error_weight
            if code_config.chase_inner_decoder_max_error_weight is not None
            else config.decoders.chase_inner_decoder_max_error_weight
        )

        if chase_p > code_config.n:
            errors.append(
                f"{code_config.name}: Chase p={chase_p} больше длины n={code_config.n}"
            )
        if syndrome_t > code_config.n:
            errors.append(
                f"{code_config.name}: syndrome t={syndrome_t} больше длины n={code_config.n}"
            )
        if chase_t > code_config.n:
            errors.append(
                f"{code_config.name}: Chase t={chase_t} больше длины n={code_config.n}"
            )
        if config.decoders.run_chase and chase_p >= 12:
            warnings.append(
                f"{code_config.name}: Chase p={chase_p} требует {2 ** chase_p:,} шаблонов"
            )
        if (
            (config.decoders.run_hard_mld or config.decoders.run_soft_mld)
            and code_config.k > config.decoders.max_k_for_mld
        ):
            warnings.append(
                f"{code_config.name}: MLD будет пропущен, k={code_config.k} > "
                f"max_k_for_mld={config.decoders.max_k_for_mld}"
            )

    return ValidationResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        report=config.estimate_workload(),
    )


def builtin_presets() -> dict[str, list[dict[str, Any]]]:
    return {
        "codes": [
            {"id": name, "name": name, "config": value.to_json_dict()}
            for name, value in CODE_PRESETS.items()
        ],
        "experiments": [
            {"id": name, "name": name, "config": value.to_json_dict()}
            for name, value in RESEARCH_PRESETS.items()
        ],
    }
