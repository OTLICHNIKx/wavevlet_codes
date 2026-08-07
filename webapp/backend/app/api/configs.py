import json

from fastapi import APIRouter, HTTPException

from app.core.config import PRESETS_DIR
from app.core.security import make_slug
from app.models.api import UserPresetRequest
from app.models.config import ResearchConfigSchema, ValidationResponse
from app.services.config_adapter import builtin_presets, validate_schema


router = APIRouter(prefix="/api", tags=["configs"])


@router.get("/config-schema")
def config_schema() -> dict:
    return ResearchConfigSchema.model_json_schema()


@router.get("/presets")
def presets() -> dict:
    result = builtin_presets()
    result["user"] = []
    for path in sorted(PRESETS_DIR.glob("*.json")):
        try:
            result["user"].append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return result


@router.post("/configs/validate", response_model=ValidationResponse)
def validate_config(config: ResearchConfigSchema) -> ValidationResponse:
    return validate_schema(config)


@router.post("/presets")
def save_user_preset(payload: UserPresetRequest) -> dict:
    slug = make_slug(payload.name)
    data = {
        "id": slug,
        "name": payload.name,
        "config": payload.config.model_dump(),
    }
    (PRESETS_DIR / f"{slug}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data


@router.delete("/presets/{preset_id}")
def delete_user_preset(preset_id: str) -> dict[str, bool]:
    slug = make_slug(preset_id)
    if slug != preset_id:
        raise HTTPException(status_code=400, detail="Недопустимый идентификатор пресета")
    path = PRESETS_DIR / f"{slug}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Пользовательский пресет не найден")
    path.unlink()
    return {"deleted": True}
