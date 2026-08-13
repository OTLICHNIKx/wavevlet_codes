import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.config import RESULTS_ROOT
from app.core.security import resolve_results_dir
from app.db.database import SessionLocal
from app.models.api import ExperimentCreate, ExperimentResponse, ResultDataResponse
from app.models.experiment import Experiment, ExperimentSource, ExperimentStatus
from app.services.csv_import import CsvValidationError
from app.services.experiment_manager import manager
from app.services.results_reader import read_summary, result_schema


router = APIRouter(prefix="/api/experiments", tags=["experiments"])


def _response(experiment: Experiment) -> ExperimentResponse:
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        status=experiment.status,
        source=experiment.source.value
        if hasattr(experiment.source, "value")
        else str(experiment.source),
        created_at=experiment.created_at,
        started_at=experiment.started_at,
        finished_at=experiment.finished_at,
        results_dir=experiment.results_dir,
        exit_code=experiment.exit_code,
        progress_completed=experiment.progress_completed,
        progress_total=experiment.progress_total,
        progress=json.loads(experiment.progress_payload or "{}"),
        error_message=experiment.error_message,
        config=json.loads(experiment.config_json),
        runtime_config_available=experiment.source != ExperimentSource.imported_csv,
    )


def _get_or_404(experiment_id: str) -> Experiment:
    experiment = manager.get(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Эксперимент не найден")
    return experiment


@router.get("", response_model=list[ExperimentResponse])
def list_experiments(
    status: ExperimentStatus | None = None,
) -> list[ExperimentResponse]:
    with SessionLocal() as session:
        statement = select(Experiment).order_by(Experiment.created_at.desc())
        if status is not None:
            statement = statement.where(Experiment.status == status)
        return [_response(item) for item in session.scalars(statement).all()]


@router.post("", response_model=ExperimentResponse, status_code=201)
def create_experiment(payload: ExperimentCreate) -> ExperimentResponse:
    try:
        experiment = manager.create(payload.name, payload.description, payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _response(experiment)


@router.post("/import/csv", response_model=ExperimentResponse, status_code=201)
async def import_csv_experiment(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(default=""),
) -> ExperimentResponse:
    """
    Импортирует уже рассчитанный summary.csv как Imported Experiment.

    Никакие Monte-Carlo вычисления не выполняются. Файл строго
    валидируется (schema + semantics) до создания эксперимента.
    """
    if not name.strip():
        raise HTTPException(
            status_code=422, detail={"errors": ["Имя эксперимента не может быть пустым"]}
        )

    raw_bytes = await file.read()

    try:
        experiment = manager.import_csv(
            name=name,
            description=description,
            # Имя файла сохраняется только для отображения и никогда
            # не используется как filesystem path.
            filename=file.filename or "summary.csv",
            raw_bytes=raw_bytes,
        )
    except CsvValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc

    return _response(experiment)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: str) -> ExperimentResponse:
    return _response(_get_or_404(experiment_id))


@router.post("/{experiment_id}/cancel")
def cancel_experiment(experiment_id: str) -> dict[str, bool]:
    _get_or_404(experiment_id)
    return {"cancelled": manager.cancel(experiment_id)}


@router.post("/{experiment_id}/rerun", response_model=ExperimentResponse)
def rerun_experiment(experiment_id: str) -> ExperimentResponse:
    source = _get_or_404(experiment_id)
    from app.models.config import ResearchConfigSchema

    config = ResearchConfigSchema.model_validate(json.loads(source.config_json))
    config.results_dir = ""
    experiment = manager.create(f"{source.name} (повтор)", source.description, config)
    return _response(experiment)


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str) -> dict[str, bool]:
    experiment = _get_or_404(experiment_id)
    if experiment.status in {
        ExperimentStatus.running,
        ExperimentStatus.validating,
        ExperimentStatus.cancelling,
    }:
        raise HTTPException(status_code=409, detail="Сначала отмените эксперимент")
    with SessionLocal() as session:
        record = session.get(Experiment, experiment_id)
        if record is not None:
            session.delete(record)
            session.commit()
    return {"deleted": True}


@router.delete("/{experiment_id}/results")
def delete_results(experiment_id: str, confirm: bool = False) -> dict[str, bool]:
    experiment = _get_or_404(experiment_id)
    if not confirm:
        raise HTTPException(status_code=400, detail="Требуется confirm=true")
    if experiment.status in {
        ExperimentStatus.running,
        ExperimentStatus.validating,
        ExperimentStatus.cancelling,
    }:
        raise HTTPException(status_code=409, detail="Нельзя удалять активные результаты")
    try:
        path = resolve_results_dir(experiment.results_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.is_relative_to(RESULTS_ROOT) or not path.is_dir():
        raise HTTPException(status_code=400, detail="Недопустимый каталог результатов")
    shutil.rmtree(path)
    return {"deleted": True}


@router.get("/{experiment_id}/logs")
def experiment_logs(
    experiment_id: str, tail: int = Query(default=500, ge=1, le=5000)
) -> dict[str, Any]:
    experiment = _get_or_404(experiment_id)
    return {"lines": manager.log(experiment, tail=tail)}


@router.get("/{experiment_id}/events")
async def experiment_events(experiment_id: str) -> StreamingResponse:
    _get_or_404(experiment_id)

    async def stream():
        last_payload = ""
        while True:
            experiment = manager.get(experiment_id)
            if experiment is None:
                break
            payload = _response(experiment).model_dump_json()
            if payload != last_payload:
                yield f"data: {payload}\n\n"
                last_payload = payload
            if experiment.status in {
                ExperimentStatus.completed,
                ExperimentStatus.failed,
                ExperimentStatus.cancelled,
                ExperimentStatus.interrupted,
            }:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/{experiment_id}/results/schema")
def results_schema(experiment_id: str) -> dict[str, Any]:
    experiment = _get_or_404(experiment_id)
    try:
        return result_schema(experiment.results_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{experiment_id}/results/data", response_model=ResultDataResponse)
def results_data(
    experiment_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=5000),
) -> ResultDataResponse:
    experiment = _get_or_404(experiment_id)
    try:
        columns, rows = read_summary(experiment.results_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResultDataResponse(
        columns=columns, rows=rows[offset : offset + limit], total=len(rows)
    )
