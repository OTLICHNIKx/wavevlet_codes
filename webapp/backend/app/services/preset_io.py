"""Portable, data-only JSON format for custom presets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.models.config import ResearchConfigSchema


PRESET_SCHEMA_VERSION = 1
PRESET_FORMAT = "wavelet-code-preset"
MAX_PRESET_BYTES = 2 * 1024 * 1024


class PresetValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class ParsedPreset:
    name: str
    description: str
    config: ResearchConfigSchema


def build_preset_document(
    *, name: str, description: str, config: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": PRESET_SCHEMA_VERSION,
        "format": PRESET_FORMAT,
        "name": name,
        "description": description,
        "config": config,
    }


def encode_preset_document(document: dict[str, Any]) -> bytes:
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")


def parse_and_validate_preset(raw_bytes: bytes) -> ParsedPreset:
    if not raw_bytes:
        raise PresetValidationError(["Preset JSON файл пуст"])
    if len(raw_bytes) > MAX_PRESET_BYTES:
        raise PresetValidationError(
            [f"Preset JSON превышает допустимый размер ({MAX_PRESET_BYTES} байт)"]
        )
    try:
        document = json.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PresetValidationError([f"Не удалось разобрать preset JSON: {exc}"]) from exc
    if not isinstance(document, dict):
        raise PresetValidationError(["Preset JSON должен быть JSON-объектом"])

    errors: list[str] = []
    version = document.get("schema_version")
    if version != PRESET_SCHEMA_VERSION:
        errors.append(f"Unsupported preset version: {version!r}")
    if document.get("format") != PRESET_FORMAT:
        errors.append(f"Неизвестный формат preset: {document.get('format')!r}")
    name = document.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("Preset name должен быть непустой строкой")
    description = document.get("description", "")
    if not isinstance(description, str):
        errors.append("Preset description должен быть строкой")
    config_data = document.get("config")
    if not isinstance(config_data, dict):
        errors.append("Preset config должен быть JSON-объектом")
    if errors:
        raise PresetValidationError(errors)

    try:
        config = ResearchConfigSchema.model_validate(config_data)
    except ValidationError as exc:
        raise PresetValidationError(
            [f"Invalid preset config: {error['loc']}: {error['msg']}" for error in exc.errors()]
        ) from exc
    return ParsedPreset(
        name=name.strip(),
        description=description,
        config=config,
    )
