"""API усреднённой Монте-Карло статистики (wavelet-эксперимент).

Читает длинные CSV вида code,channel,decoder,parameter,metric,mean,std,
ci_low,ci_high,seeds,words, которые генерирует
research/run_wavelet_channel_decoder_experiment.py
(wavelet_channel_decoder_statistics_all_metrics.csv).

Два источника файлов:
  * каталог эксперимента по умолчанию: <репозиторий>/results
    (переопределяется MC_STATS_DIR);
  * загруженные через веб (аналогично импорту экспериментов):
    <WEBAPP_DATA_ROOT>/mc_stats (переопределяется MC_STATS_UPLOADS_DIR).

Имена файлов ограничены списком каталогов и схемой с колонкой metric
(защита от path traversal и мусорных CSV). Загруженные файлы можно
удалять, файлы из results — только просматривать.
"""

from __future__ import annotations

import csv
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import WEBAPP_DATA_ROOT

router = APIRouter(prefix="/api/mc-stats", tags=["mc-stats"])

_REPO_ROOT = Path(__file__).resolve().parents[4]

ALL_METRICS_HEADER = {
    "code", "channel", "decoder", "parameter", "metric",
    "mean", "std", "ci_low", "ci_high",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _safe_label(text: str) -> str:
    """Юникод-безопасный slug: буквы/цифры/_/-/., без разделителей пути."""
    cleaned = re.sub(r"[^\w.\-]+", "_", text.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("._-")[:64]
    return cleaned or "mc_stats"


def stats_dir() -> Path:
    return Path(os.environ.get("MC_STATS_DIR", str(_REPO_ROOT / "results")))


def uploads_dir() -> Path:
    return Path(
        os.environ.get(
            "MC_STATS_UPLOADS_DIR", str(WEBAPP_DATA_ROOT / "mc_stats")
        )
    )


def _is_stats_csv(path: Path) -> bool:
    if "statistic" not in path.name.lower():
        return False
    try:
        with path.open(encoding="utf-8") as handle:
            header = next(csv.reader(handle), [])
    except (OSError, UnicodeDecodeError):
        return False
    return ALL_METRICS_HEADER.issubset(set(header))


def _scan(directory: Path, source: str) -> list[dict[str, str]]:
    if not directory.is_dir():
        return []
    return [
        {"name": path.name, "source": source}
        for path in sorted(directory.glob("*.csv"))
        if _is_stats_csv(path)
    ]


def available_items() -> list[dict[str, str]]:
    """Список доступных файлов: сначала локальный results, затем uploads."""
    items = _scan(stats_dir(), "results")
    taken = {item["name"] for item in items}
    for item in _scan(uploads_dir(), "uploaded"):
        if item["name"] in taken:
            continue
        items.append(item)
    return items


def available_files() -> list[str]:
    return [item["name"] for item in available_items()]


def _resolve(name: str) -> tuple[Path, str]:
    for item in available_items():
        if item["name"] == name:
            directory = (
                uploads_dir()
                if item["source"] == "uploaded"
                else stats_dir()
            )
            return directory / name, item["source"]
    raise HTTPException(status_code=404, detail=f"Файл {name!r} недоступен")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = ALL_METRICS_HEADER
        if not reader.fieldnames or not required.issubset(
            set(reader.fieldnames)
        ):
            raise HTTPException(
                status_code=422,
                detail="CSV не имеет схемы all-metrics статистики",
            )
        rows: list[dict[str, Any]] = []
        for raw in reader:
            try:
                rows.append(
                    {
                        "code": raw["code"],
                        "channel": raw["channel"],
                        "decoder": raw["decoder"],
                        "parameter": float(raw["parameter"]),
                        "metric": raw["metric"],
                        "mean": float(raw["mean"]),
                        "std": float(raw["std"]),
                        "ci_low": float(raw["ci_low"]),
                        "ci_high": float(raw["ci_high"]),
                        "seeds": int(raw.get("seeds") or 0),
                        "words": int(raw.get("words") or 0),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
        return rows


def _validate_stats_bytes(raw: bytes) -> None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422, detail="CSV должен быть в кодировке UTF-8",
        ) from exc
    reader = csv.reader(text.splitlines())
    header = next(reader, [])
    if not ALL_METRICS_HEADER.issubset(set(header)):
        raise HTTPException(
            status_code=422,
            detail=(
                "CSV не имеет схемы all-metrics статистики "
                "(нужны колонки code,channel,decoder,parameter,metric,"
                "mean,std,ci_low,ci_high)"
            ),
        )
    valid_rows = 0
    for record in reader:
        if len(record) >= len(header):
            valid_rows += 1
    if valid_rows == 0:
        raise HTTPException(
            status_code=422, detail="CSV не содержит ни одной строки данных"
        )


@router.get("")
def list_files() -> dict[str, Any]:
    items = available_items()
    return {
        "files": [item["name"] for item in items],
        "items": items,
        "dir": str(stats_dir()),
        "uploads_dir": str(uploads_dir()),
    }


@router.post("/upload", status_code=201)
async def upload_stats(
    file: UploadFile = File(...),
    name: str = Form(default=""),
) -> dict[str, str]:
    """
    Загружает all-metrics CSV Монте-Карло статистики (аналог импорта
    экспериментов): валидация схемы до сохранения, хранение в каталоге
    загрузок, выход за его пределы невозможен.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422, detail="Ожидается файл .csv",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="Пустой файл")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Файл больше лимита {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    _validate_stats_bytes(raw)

    label = name.strip() or filename.removesuffix(".csv") or "mc_stats"
    directory = uploads_dir()
    directory.mkdir(parents=True, exist_ok=True)
    base = _safe_label(label)
    stored = f"{base}_{uuid.uuid4().hex[:8]}_statistics_all_metrics.csv"
    path = directory / stored
    if path.exists():
        raise HTTPException(status_code=409, detail="Такое имя уже занято")
    path.write_bytes(raw)
    return {"name": stored, "source": "uploaded"}


@router.delete("/files/{name}")
def delete_uploaded(name: str) -> dict[str, bool]:
    _path, source = _resolve(name)
    if source != "uploaded":
        raise HTTPException(
            status_code=403,
            detail="Можно удалять только загруженные файлы",
        )
    _path.unlink(missing_ok=True)
    return {"deleted": True}


@router.get("/series")
def series(
    file: str | None = None,
    code: str | None = None,
    codes: str | None = None,
    channel: str | None = None,
    metric: str | None = None,
    decoders: str | None = None,
) -> dict[str, Any]:
    items = available_items()
    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                "CSV Монте-Карло статистики не найден; запустите "
                "research/run_wavelet_channel_decoder_experiment.py "
                "или загрузите файл"
            ),
        )
    name = file or items[0]["name"]
    path, _source = _resolve(name)
    rows = _load_rows(path)

    universe = {
        "codes": sorted({r["code"] for r in rows}),
        "channels": sorted({r["channel"] for r in rows}),
        "decoders": sorted({r["decoder"] for r in rows}),
        "metrics": sorted({r["metric"] for r in rows}),
    }
    wanted_decoders = (
        {item.strip() for item in decoders.split(",") if item.strip()}
        if decoders
        else None
    )
    wanted_codes = (
        {item.strip() for item in codes.split(",") if item.strip()}
        if codes
        else None
    )
    filtered = [
        r
        for r in rows
        if (code is None or r["code"] == code)
        and (wanted_codes is None or r["code"] in wanted_codes)
        and (channel is None or r["channel"] == channel)
        and (metric is None or r["metric"] == metric)
        and (wanted_decoders is None or r["decoder"] in wanted_decoders)
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in filtered:
        grouped.setdefault((row["code"], row["decoder"]), []).append(row)
    out_series = []
    for code_name in universe["codes"]:
        for decoder in universe["decoders"]:
            points = sorted(
                grouped.get((code_name, decoder), []),
                key=lambda r: r["parameter"],
            )
            if not points:
                continue
            out_series.append(
                {
                    "code": code_name,
                    "decoder": decoder,
                    "x": [p["parameter"] for p in points],
                    "y": [p["mean"] for p in points],
                    "std": [p["std"] for p in points],
                    "ci_low": [p["ci_low"] for p in points],
                    "ci_high": [p["ci_high"] for p in points],
                    "seeds": points[0]["seeds"],
                    "words": points[0]["words"],
                }
            )
    return {
        "file": name,
        "selected": {
            "code": code or (universe["codes"][0] if universe["codes"] else None),
            "channel": channel
            or (universe["channels"][0] if universe["channels"] else None),
            "metric": metric
            or (universe["metrics"][0] if universe["metrics"] else None),
        },
        "universe": universe,
        "series": out_series,
    }
