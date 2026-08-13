"""Общие типизированные модели API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.config import ResearchConfigSchema
from app.models.experiment import ExperimentStatus


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    config: ResearchConfigSchema


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: str
    status: ExperimentStatus
    source: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    results_dir: str
    exit_code: int | None
    progress_completed: int
    progress_total: int
    progress: dict[str, Any]
    error_message: str
    config: dict[str, Any]
    runtime_config_available: bool = True


class ResultDataResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total: int


class PlotPreviewRequest(BaseModel):
    experiment_ids: list[str] = Field(min_length=1)
    codes: list[str] = Field(default_factory=list)
    decoders: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=lambda: ["frame_error_rate"])
    ebn0_min: float | None = None
    ebn0_max: float | None = None
    zero_mode: str = "hide"
    epsilon: float = Field(default=1e-8, gt=0)


class PlotExportRequest(PlotPreviewRequest):
    format: str = "csv"


class UserPresetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    config: ResearchConfigSchema


class CsvImportErrorResponse(BaseModel):
    errors: list[str]
