"""Безопасный экспорт/импорт portable experiment package (``.zip``).

Формат пакета:

    manifest.json          (обязателен)
    summary.csv            (обязателен)
    runtime_config.json    (опционален)
    code_metadata.json      (опционален)
    experiment.log          (опционален)

Импорт читает ТОЛЬКО эти пять фиксированных имён файлов из архива и
полностью игнорирует остальные записи. Путь на диске всегда строится
нами самими (не из архива), поэтому zip slip / path traversal здесь
структурно невозможны — обычный небезопасный ``extractall`` не
используется вообще.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass
from typing import Any

from app.services.csv_import import CsvValidationError, parse_and_validate_csv


SCHEMA_VERSION = 1
PACKAGE_FORMAT = "wavelet-code-experiment"

MANIFEST_NAME = "manifest.json"
SUMMARY_NAME = "summary.csv"
RUNTIME_CONFIG_NAME = "runtime_config.json"
CODE_METADATA_NAME = "code_metadata.json"
LOG_NAME = "experiment.log"

# Единственные имена файлов, которые импорт когда-либо читает из архива.
SAFE_MEMBER_NAMES = {
    MANIFEST_NAME,
    SUMMARY_NAME,
    RUNTIME_CONFIG_NAME,
    CODE_METADATA_NAME,
    LOG_NAME,
}

MAX_ZIP_BYTES = 100 * 1024 * 1024  # 100 MiB — общий размер загружаемого архива
MAX_MEMBER_BYTES = 60 * 1024 * 1024  # 60 MiB — заявленный размер одного файла
MAX_EXTRACTED_BYTES = 100 * 1024 * 1024  # 100 MiB — сумма распакованных файлов
MAX_MEMBERS = 200  # защита от zip-бомб с огромным числом записей


class PackageValidationError(ValueError):
    """Ошибка валидации experiment package со списком конкретных причин."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class ParsedPackage:
    manifest: dict[str, Any]
    summary_csv_bytes: bytes
    summary_rows: list[dict[str, Any]]
    runtime_config: dict[str, Any] | None
    code_metadata: list[dict[str, Any]] | None
    experiment_log: str | None


def build_manifest(
    *, name: str, created_at: str, status: str, experiment_id: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "format": PACKAGE_FORMAT,
        "name": name,
        "created_at": created_at,
        "status": status,
        "experiment_id": experiment_id,
    }


def build_zip(
    *,
    manifest: dict[str, Any],
    summary_csv_bytes: bytes,
    runtime_config_bytes: bytes | None,
    code_metadata_bytes: bytes | None,
    experiment_log_bytes: bytes | None,
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2)
        )
        archive.writestr(SUMMARY_NAME, summary_csv_bytes)
        if runtime_config_bytes is not None:
            archive.writestr(RUNTIME_CONFIG_NAME, runtime_config_bytes)
        if code_metadata_bytes is not None:
            archive.writestr(CODE_METADATA_NAME, code_metadata_bytes)
        if experiment_log_bytes is not None:
            archive.writestr(LOG_NAME, experiment_log_bytes)
    return buffer.getvalue()


def parse_and_validate_package(raw_bytes: bytes) -> ParsedPackage:
    """
    Разбирает и валидирует experiment package.

    Выполняет только чтение и проверку: никаких Monte-Carlo
    вычислений и никакого исполнения содержимого архива.
    """
    if len(raw_bytes) == 0:
        raise PackageValidationError(["Пакет пуст"])
    if len(raw_bytes) > MAX_ZIP_BYTES:
        raise PackageValidationError(
            [f"Пакет превышает допустимый размер ({MAX_ZIP_BYTES} байт)"]
        )

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile as exc:
        raise PackageValidationError([f"Не удалось открыть архив: {exc}"]) from exc

    infos = archive.infolist()
    if len(infos) > MAX_MEMBERS:
        raise PackageValidationError(["В архиве слишком много файлов"])

    members_by_name: dict[str, zipfile.ZipInfo] = {}
    total_extracted_size = 0
    for info in infos:
        if info.is_dir():
            continue
        if _is_unsafe_member_name(info.filename):
            raise PackageValidationError(
                [f"Недопустимый путь в архиве: {info.filename!r}"]
            )
        if info.filename not in SAFE_MEMBER_NAMES:
            raise PackageValidationError(
                [f"Недопустимый файл в архиве: {info.filename!r}"]
            )
        if info.filename in members_by_name:
            raise PackageValidationError(
                [f"Файл {info.filename} указан в архиве несколько раз"]
            )
        if info.file_size > MAX_MEMBER_BYTES:
            raise PackageValidationError(
                [f"Файл {info.filename} превышает допустимый размер"]
            )
        total_extracted_size += info.file_size
        if total_extracted_size > MAX_EXTRACTED_BYTES:
            raise PackageValidationError(
                ["Суммарный распакованный размер файлов превышает допустимый"]
            )
        members_by_name[info.filename] = info

    if MANIFEST_NAME not in members_by_name:
        raise PackageValidationError(["Missing required file: manifest.json"])
    if SUMMARY_NAME not in members_by_name:
        raise PackageValidationError(["Missing required file: summary.csv"])

    try:
        manifest = json.loads(
            archive.read(members_by_name[MANIFEST_NAME]).decode("utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PackageValidationError([f"manifest.json повреждён: {exc}"]) from exc

    manifest_errors = _validate_manifest(manifest)
    if manifest_errors:
        raise PackageValidationError(manifest_errors)

    summary_bytes = archive.read(members_by_name[SUMMARY_NAME])
    try:
        csv_result = parse_and_validate_csv(summary_bytes)
    except CsvValidationError as exc:
        raise PackageValidationError(exc.errors) from exc

    runtime_config: dict[str, Any] | None = None
    if RUNTIME_CONFIG_NAME in members_by_name:
        try:
            runtime_config = json.loads(
                archive.read(members_by_name[RUNTIME_CONFIG_NAME]).decode("utf-8")
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PackageValidationError(
                [f"runtime_config.json повреждён: {exc}"]
            ) from exc
        if not isinstance(runtime_config, dict):
            raise PackageValidationError(
                ["runtime_config.json должен быть JSON-объектом"]
            )

    code_metadata: list[dict[str, Any]] | None = None
    if CODE_METADATA_NAME in members_by_name:
        try:
            code_metadata = json.loads(
                archive.read(members_by_name[CODE_METADATA_NAME]).decode("utf-8")
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PackageValidationError(
                [f"code_metadata.json повреждён: {exc}"]
            ) from exc
        if not isinstance(code_metadata, list) or not all(
            isinstance(item, dict) for item in code_metadata
        ):
            raise PackageValidationError(
                ["code_metadata.json должен быть массивом JSON-объектов"]
            )

    experiment_log: str | None = None
    if LOG_NAME in members_by_name:
        experiment_log = archive.read(members_by_name[LOG_NAME]).decode(
            "utf-8", errors="replace"
        )

    return ParsedPackage(
        manifest=manifest,
        summary_csv_bytes=summary_bytes,
        summary_rows=csv_result.rows,
        runtime_config=runtime_config,
        code_metadata=code_metadata,
        experiment_log=experiment_log,
    )


def _validate_manifest(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["manifest.json должен быть JSON-объектом"]

    errors: list[str] = []
    schema_version = manifest.get("schema_version")
    if schema_version is None:
        errors.append("manifest.json: отсутствует schema_version")
    elif schema_version != SCHEMA_VERSION:
        errors.append(f"Unsupported experiment package version: {schema_version!r}")

    format_value = manifest.get("format")
    if format_value != PACKAGE_FORMAT:
        errors.append(f"Неизвестный формат пакета: {format_value!r}")

    for key in ("name", "created_at", "status"):
        value = manifest.get(key)
        if value is None:
            errors.append(f"manifest.json: отсутствует поле {key}")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"manifest.json: поле {key} должно быть непустой строкой")

    if manifest.get("status") not in (None, "completed"):
        errors.append("Импортировать можно только завершённый эксперимент")

    return errors


def _is_unsafe_member_name(filename: str) -> bool:
    normalized = filename.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        return True
    return any(part == ".." for part in normalized.split("/"))
