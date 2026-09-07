import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.api import UserPresetRequest
from app.models.config import ResearchConfigSchema, ValidationResponse
from app.models.experiment import CustomPreset
from app.services.config_adapter import builtin_presets, validate_schema
from app.services.custom_presets import create_custom_preset, preset_response
from app.services.experiment_preview import build_experiment_preview
from app.services.preset_io import (
    PresetValidationError,
    build_preset_document,
    encode_preset_document,
    parse_and_validate_preset,
)
from app.core.security import make_slug


router = APIRouter(prefix="/api", tags=["configs"])


@router.get("/config-schema")
def config_schema() -> dict:
    return ResearchConfigSchema.model_json_schema()


@router.get("/presets")
def presets() -> dict:
    result = builtin_presets()
    with SessionLocal() as session:
        records = session.scalars(
            select(CustomPreset).order_by(CustomPreset.updated_at.desc())
        ).all()
        result["user"] = [preset_response(record) for record in records]
    return result


@router.post("/configs/validate", response_model=ValidationResponse)
def validate_config(config: ResearchConfigSchema) -> ValidationResponse:
    return validate_schema(config)


@router.post("/configs/preview")
def preview_config(config: ResearchConfigSchema) -> dict:
    return build_experiment_preview(config)


@router.post("/presets", status_code=201)
def save_user_preset(payload: UserPresetRequest) -> dict:
    try:
        record = create_custom_preset(
            name=payload.name,
            description=payload.description,
            config=payload.config,
            session_factory=SessionLocal,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"errors": [str(exc)]}) from exc
    return preset_response(record)


@router.post("/presets/import", status_code=201)
async def import_user_preset(file: UploadFile = File(...)) -> dict:
    try:
        parsed = parse_and_validate_preset(await file.read())
        record = create_custom_preset(
            name=parsed.name,
            description=parsed.description,
            config=parsed.config,
            session_factory=SessionLocal,
        )
    except PresetValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"errors": [str(exc)]}) from exc
    return preset_response(record)


@router.get("/presets/{preset_id}")
def get_user_preset(preset_id: str) -> dict:
    with SessionLocal() as session:
        record = session.get(CustomPreset, preset_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Пользовательский пресет не найден")
        return preset_response(record)


@router.put("/presets/{preset_id}")
def update_user_preset(preset_id: str, payload: UserPresetRequest) -> dict:
    _validate_preset_config(payload.config)
    with SessionLocal() as session:
        record = session.get(CustomPreset, preset_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Пользовательский пресет не найден")
        record.name = payload.name.strip()
        record.description = payload.description
        record.config_json = json.dumps(payload.config.model_dump(), ensure_ascii=False)
        record.updated_at = _utcnow()
        session.commit()
        session.refresh(record)
        return preset_response(record)


@router.post("/presets/{preset_id}/duplicate", status_code=201)
def duplicate_user_preset(preset_id: str) -> dict:
    with SessionLocal() as session:
        source = session.get(CustomPreset, preset_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Пользовательский пресет не найден")
        now = _utcnow()
        duplicate = CustomPreset(
            id=str(uuid.uuid4()),
            name=f"{source.name} (копия)",
            description=source.description,
            created_at=now,
            updated_at=now,
            config_json=source.config_json,
            schema_version=source.schema_version,
        )
        session.add(duplicate)
        session.commit()
        session.refresh(duplicate)
        return preset_response(duplicate)


@router.post("/presets/{preset_id}/preview")
def preview_user_preset(preset_id: str) -> dict:
    with SessionLocal() as session:
        record = session.get(CustomPreset, preset_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Пользовательский пресет не найден")
        schema = ResearchConfigSchema.model_validate_json(record.config_json)
    return build_experiment_preview(schema)


@router.get("/presets/{preset_id}/export")
def export_user_preset(preset_id: str) -> Response:
    with SessionLocal() as session:
        record = session.get(CustomPreset, preset_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Пользовательский пресет не найден")
        document = build_preset_document(
            name=record.name,
            description=record.description,
            config=json.loads(record.config_json),
        )
        filename = f"{make_slug(record.name, fallback='preset')}.preset.json"
    return Response(
        content=encode_preset_document(document),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/presets/{preset_id}")
def delete_user_preset(preset_id: str) -> dict[str, bool]:
    with SessionLocal() as session:
        record = session.get(CustomPreset, preset_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Пользовательский пресет не найден")
        session.delete(record)
        session.commit()
    return {"deleted": True}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _validate_preset_config(config: ResearchConfigSchema) -> None:
    validation = validate_schema(config)
    if not validation.valid:
        raise HTTPException(status_code=422, detail={"errors": validation.errors})

