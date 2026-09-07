"""Shared persistence helpers for SQLite-backed custom presets."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.db.database import SessionLocal
from app.models.config import ResearchConfigSchema
from app.models.experiment import CustomPreset
from app.services.config_adapter import validate_schema


def create_custom_preset(
    *,
    name: str,
    description: str,
    config: ResearchConfigSchema,
    session_factory: sessionmaker | None = None,
) -> CustomPreset:
    validation = validate_schema(config)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))

    now = _utcnow()
    record = CustomPreset(
        id=str(uuid.uuid4()),
        name=name.strip(),
        description=description,
        created_at=now,
        updated_at=now,
        config_json=json.dumps(config.model_dump(), ensure_ascii=False),
        schema_version=1,
    )
    factory = session_factory or SessionLocal
    with factory() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


def preset_response(record: CustomPreset) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "description": record.description,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "schema_version": record.schema_version,
        "config": json.loads(record.config_json),
    }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
