"""Pydantic-схемы конфигурации эксперимента для API."""

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator


CodeFamily = Literal["wavelet", "bch", "bch_derived"]


class CodeConfigSchema(BaseModel):
    """Конфигурация одного кода для API."""

    name: str = Field(min_length=1, max_length=255)
    family: CodeFamily
    n: int = Field(gt=0)
    k: int = Field(gt=0)

    # Wavelet
    h: list[int] | None = None
    g: list[int] | None = None
    a: int = 1
    b: int = 1
    shift: int = 1

    # BCH
    bch_m: int | None = None
    bch_designed_distance: int | None = None
    bch_primitive_polynomial: int | None = None
    bch_first_root: int = 1

    # BCH-derived
    bch_shortening_count: int | None = None
    bch_puncture_count: int | None = None
    bch_puncture_coordinates: list[int] | None = None

    expected_min_distance: int | None = None

    syndrome_max_error_weight: int | None = Field(default=None, ge=0)
    chase_inner_decoder_max_error_weight: int | None = Field(default=None, ge=0)
    chase_unreliable_positions_count: int | None = Field(default=None, gt=0)

    @field_validator("h", "g")
    @classmethod
    def binary_vector(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        for value in v:
            if value not in (0, 1):
                raise ValueError(
                    f"Вектор должен состоять из 0 и 1, получено {value}"
                )
        return v

    @field_validator("k")
    @classmethod
    def k_less_than_n(cls, v: int, info) -> int:
        n = info.data.get("n")
        if n is not None and v >= n:
            raise ValueError("k должно быть меньше n")
        return v


class DecoderConfigSchema(BaseModel):
    """Настройки декодеров."""

    run_syndrome: bool = True
    run_hard_mld: bool = False
    run_soft_mld: bool = False
    run_chase: bool = True

    syndrome_max_error_weight: int = Field(default=2, ge=0)
    chase_inner_decoder_max_error_weight: int = Field(default=2, ge=0)
    chase_unreliable_positions_count: int = Field(default=4, gt=0)
    max_k_for_mld: int = Field(default=16, gt=0)


class ResearchConfigSchema(BaseModel):
    """Полная конфигурация исследования для API."""

    message_count: int = Field(gt=0)
    message_seed: int
    noise_seed: int

    ebn0_db_values: list[float] = Field(min_length=1)
    codes: list[CodeConfigSchema] = Field(min_length=1)
    decoders: DecoderConfigSchema = Field(default_factory=DecoderConfigSchema)

    results_dir: str = ""  # заполняется backend'ом

    @field_validator("ebn0_db_values")
    @classmethod
    def ebn0_finite(cls, v: list[float]) -> list[float]:
        for x in v:
            if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
                raise ValueError(f"Eb/N0 должен быть конечным числом, получено {x!r}")
        return [float(x) for x in v]


class EbN0RangeRequest(BaseModel):
    """Запрос на генерацию диапазона Eb/N0."""

    mode: Literal["range", "explicit"]
    start: float | None = None
    stop: float | None = None
    step: float | None = None
    values: list[float] | None = None


class ValidationResponse(BaseModel):
    """Результат /api/configs/validate."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    report: dict = Field(default_factory=dict)
