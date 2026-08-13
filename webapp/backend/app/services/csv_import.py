"""Безопасный импорт готового ``summary.csv`` без Monte-Carlo вычислений.

Модуль отвечает только за парсинг и валидацию (schema + semantics).
Создание Imported Experiment и запись файлов на диск выполняются
в ``app.services.experiment_manager``.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

from app.services.results_reader import convert_csv_value


# Минимально обязательные колонки: то, что уже требуется существующему UI
# для построения графиков/таблиц (см. research/runner.py: write_summary_csv).
REQUIRED_COLUMNS: tuple[str, ...] = (
    "code_name",
    "code_family",
    "n",
    "k",
    "decoder",
    "ebn0_db",
    "message_count",
    "ber",
    "frame_error_rate",
)

# Защита от неограниченной по размеру загрузки.
MAX_CSV_BYTES = 50 * 1024 * 1024  # 50 MiB

_TOLERANCE = 1e-6


class CsvValidationError(ValueError):
    """Ошибка валидации импортируемого CSV со списком конкретных причин."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class CsvImportResult:
    columns: list[str]
    rows: list[dict[str, Any]]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_and_validate_csv(raw_bytes: bytes) -> CsvImportResult:
    """
    Разбирает summary.csv и проверяет schema/семантику.

    Выполняет только чтение и проверку данных: никаких Monte-Carlo
    вычислений, пересчёта или сглаживания метрик.
    """
    if len(raw_bytes) == 0:
        raise CsvValidationError(["CSV файл пуст"])
    if len(raw_bytes) > MAX_CSV_BYTES:
        raise CsvValidationError(
            [f"Файл превышает допустимый размер ({MAX_CSV_BYTES} байт)"]
        )

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvValidationError([f"Файл не в кодировке UTF-8: {exc}"]) from exc

    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = [name for name in (reader.fieldnames or []) if name is not None]
        raw_rows = list(reader)
    except csv.Error as exc:
        raise CsvValidationError([f"Не удалось разобрать CSV: {exc}"]) from exc

    if not fieldnames:
        raise CsvValidationError(["CSV не содержит заголовка"])

    schema_errors = _validate_schema(fieldnames)
    if schema_errors:
        raise CsvValidationError(schema_errors)

    if not raw_rows:
        raise CsvValidationError(["CSV не содержит строк с данными"])

    rows = [
        {
            key: convert_csv_value(value)
            for key, value in row.items()
            if key is not None and value is not None
        }
        for row in raw_rows
    ]

    semantic_errors = _validate_semantics(rows)
    if semantic_errors:
        raise CsvValidationError(semantic_errors)

    return CsvImportResult(columns=fieldnames, rows=rows)


def build_synthetic_config(
    rows: list[dict[str, Any]],
    results_dir: str,
) -> dict[str, Any]:
    """
    Строит минимальный config-подобный объект исключительно из
    данных, уже присутствующих в CSV (code_name/code_family/n/k,
    ebn0_db, message_count). Ничего не придумывается.

    Используется только для отображения в существующем UI (список
    экспериментов и т.п.), не является реальным runtime_config.
    """
    codes: dict[str, dict[str, Any]] = {}
    ebn0_values: set[float] = set()
    message_counts: set[int] = set()

    for row in rows:
        name = row.get("code_name")
        if name and name not in codes:
            codes[name] = {
                "name": name,
                "family": row.get("code_family") or "wavelet",
                "n": row.get("n") or 0,
                "k": row.get("k") or 0,
            }

        ebn0 = row.get("ebn0_db")
        if _is_number(ebn0):
            ebn0_values.add(float(ebn0))

        message_count = row.get("message_count")
        if _is_number(message_count):
            message_counts.add(int(message_count))

    return {
        "message_count": max(message_counts) if message_counts else 0,
        "message_seed": 0,
        "noise_seed": 0,
        "ebn0_db_values": sorted(ebn0_values),
        "codes": list(codes.values()),
        "decoders": {
            "run_syndrome": False,
            "run_hard_mld": False,
            "run_soft_mld": False,
            "run_chase": False,
            "syndrome_max_error_weight": 0,
            "chase_inner_decoder_max_error_weight": 0,
            "chase_unreliable_positions_count": 0,
            "max_k_for_mld": 0,
        },
        "results_dir": results_dir,
    }


def _validate_schema(fieldnames: list[str]) -> list[str]:
    present = set(fieldnames)
    return [
        f"Missing required column: {column}"
        for column in REQUIRED_COLUMNS
        if column not in present
    ]


def _validate_semantics(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    group_message_count: dict[tuple[Any, Any], Any] = {}

    for index, row in enumerate(rows, start=1):
        n = row.get("n")
        k = row.get("k")
        message_count = row.get("message_count")
        ber = row.get("ber")
        fer = row.get("frame_error_rate")
        skipped = row.get("skipped") is True

        if not _is_number(n) or n <= 0:
            errors.append(f"Строка {index}: n должно быть положительным (n={n!r})")
        if not _is_number(k) or k <= 0:
            errors.append(f"Строка {index}: k должно быть положительным (k={k!r})")
        if _is_number(n) and _is_number(k) and k > n:
            errors.append(
                f"Строка {index}: k не может быть больше n (n={n}, k={k})"
            )

        if not _is_number(message_count) or message_count <= 0:
            errors.append(
                f"Строка {index}: message_count должно быть положительным "
                f"(message_count={message_count!r})"
            )

        if not skipped:
            if _is_number(ber) and not (0.0 <= float(ber) <= 1.0):
                errors.append(f"Invalid BER at row {index}: {ber}")
            if _is_number(fer) and not (0.0 <= float(fer) <= 1.0):
                errors.append(f"Invalid FER at row {index}: {fer}")

            success_count = row.get("success_count")
            failure_count = row.get("failure_count")
            if (
                _is_number(success_count)
                and _is_number(failure_count)
                and _is_number(message_count)
                and success_count + failure_count != message_count
            ):
                errors.append(
                    f"Строка {index}: success_count + failure_count "
                    f"({success_count}+{failure_count}) "
                    f"!= message_count ({message_count})"
                )

            frame_errors = row.get("frame_errors")
            if (
                _is_number(frame_errors)
                and _is_number(fer)
                and _is_number(message_count)
                and message_count > 0
            ):
                expected_fer = frame_errors / message_count
                if abs(expected_fer - fer) > _TOLERANCE:
                    errors.append(
                        f"Строка {index}: frame_error_rate={fer} не соответствует "
                        f"frame_errors/message_count={expected_fer:.6g}"
                    )

            bit_errors = row.get("bit_errors")
            total_bits = row.get("total_bits")
            if (
                _is_number(bit_errors)
                and _is_number(total_bits)
                and _is_number(ber)
                and total_bits > 0
            ):
                expected_ber = bit_errors / total_bits
                if abs(expected_ber - ber) > _TOLERANCE:
                    errors.append(
                        f"Строка {index}: ber={ber} не соответствует "
                        f"bit_errors/total_bits={expected_ber:.6g}"
                    )

        group_key = (row.get("code_name"), row.get("ebn0_db"))
        if _is_number(message_count):
            if group_key in group_message_count:
                if group_message_count[group_key] != message_count:
                    errors.append(
                        f"Строка {index}: different message_count inside same "
                        f"code/SNR result ({group_key})"
                    )
            else:
                group_message_count[group_key] = message_count

    return errors
