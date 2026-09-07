"""Pydantic-схемы конфигурации эксперимента для API."""

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CodeFamily = Literal["wavelet", "bch", "bch_derived", "goppa_derived", "reed_solomon_binary"]


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

    # Goppa-derived
    goppa_m: int | None = None
    goppa_degree: int | None = None
    goppa_support_size: int | None = None
    goppa_seed: int = 42
    # Generalized Reed-Solomon binary image.
    reed_solomon_m: int | None = Field(default=None, ge=1)
    reed_solomon_symbol_n: int | None = Field(default=None, gt=0)
    reed_solomon_symbol_k: int | None = Field(default=None, gt=0)
    reed_solomon_primitive_polynomial: int | None = Field(default=None, gt=0)
    reed_solomon_evaluation_points: list[int] | None = None
    reed_solomon_column_multipliers: list[int] | None = None
    goppa_primitive_polynomial: int | None = None

    expected_min_distance: int | None = None
    minimum_distance_exact: int | None = Field(default=None, ge=0)
    minimum_distance_lower_bound: int | None = Field(default=None, ge=0)
    minimum_distance_upper_bound: int | None = Field(default=None, ge=0)
    distance_evidence: str = ""
    verified_error_correction_radius: int | None = Field(default=None, ge=0)

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



    @model_validator(mode="after")
    def validate_reed_solomon_binary(self) -> "CodeConfigSchema":
        if self.family != "reed_solomon_binary":
            return self
        required = {
            "reed_solomon_m": self.reed_solomon_m,
            "reed_solomon_symbol_n": self.reed_solomon_symbol_n,
            "reed_solomon_symbol_k": self.reed_solomon_symbol_k,
            "reed_solomon_primitive_polynomial": self.reed_solomon_primitive_polynomial,
            "reed_solomon_evaluation_points": self.reed_solomon_evaluation_points,
            "reed_solomon_column_multipliers": self.reed_solomon_column_multipliers,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ValueError("Для reed_solomon_binary не заданы: " + ", ".join(missing))
        assert self.reed_solomon_m is not None
        assert self.reed_solomon_symbol_n is not None
        assert self.reed_solomon_symbol_k is not None
        assert self.reed_solomon_evaluation_points is not None
        assert self.reed_solomon_column_multipliers is not None
        if self.reed_solomon_symbol_k >= self.reed_solomon_symbol_n:
            raise ValueError("Для GRS требуется symbol_k < symbol_n")
        if self.reed_solomon_symbol_n > (1 << self.reed_solomon_m):
            raise ValueError("symbol_n не может превышать размер GF(2^m)")
        if self.n != self.reed_solomon_m * self.reed_solomon_symbol_n:
            raise ValueError("n должно совпадать с m * symbol_n")
        if self.k != self.reed_solomon_m * self.reed_solomon_symbol_k:
            raise ValueError("k должно совпадать с m * symbol_k")
        field_size = 1 << self.reed_solomon_m
        points = self.reed_solomon_evaluation_points
        multipliers = self.reed_solomon_column_multipliers
        if len(points) != self.reed_solomon_symbol_n or len(multipliers) != self.reed_solomon_symbol_n:
            raise ValueError("Длины evaluation_points и column_multipliers должны совпадать с symbol_n")
        if len(set(points)) != len(points):
            raise ValueError("evaluation_points должны быть уникальны")
        if any(value < 0 or value >= field_size for value in points):
            raise ValueError("evaluation_points должны принадлежать GF(2^m)")
        if any(value <= 0 or value >= field_size for value in multipliers):
            raise ValueError("column_multipliers должны быть ненулевыми элементами GF(2^m)")
        return self
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
