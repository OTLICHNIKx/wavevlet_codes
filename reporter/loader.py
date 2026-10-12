"""Поиск и чтение CSV-результатов экспериментов.

Поддерживаются два формата:

1. Bulk-прогоны ``research_results/five_families_channels/<channel>/<size>_20k/summary.csv``
   (широкая таблица runner'а: code_family, n, k, ebn0_db, ber, ...).
2. Monte Carlo ``results/mc_*/wavelet_channel_decoder_statistics[_all_metrics].csv``
   (агрегат по сидам: code, channel, decoder, parameter, mean_BER, ...).

Канал для bulk-файлов берётся из пути; для MC — из колонки ``channel``.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable

from .models import ExperimentResult, LoadedData, family_group


# Префиксы семейств от длинных к коротким, чтобы bch_derived не путать с bch.
_FAMILY_PREFIXES: tuple[str, ...] = (
    "reed_solomon_binary",
    "reed_solomon",
    "bch_derived",
    "goppa_derived",
    "wavelet",
    "goppa",
    "ldpc",
    "bch",
)

_SIZE_RE = re.compile(r"(\d+)_(\d+)")


def parse_code_name(code_name: str) -> tuple[str, int | None, int | None]:
    """Возвращает (family, n, k) из имени кода, если оно распознаётся."""
    lowered = code_name.strip().lower()
    for prefix in _FAMILY_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "_"):
            rest = lowered[len(prefix) + 1:]
            match = _SIZE_RE.match(rest)
            if match:
                return prefix, int(match.group(1)), int(match.group(2))
            return prefix, None, None
    return "unknown", None, None


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(value: object) -> int | None:
    number = _parse_float(value)
    if number is None:
        return None
    return int(number)


def _parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_bulk_summary(
    path: Path,
    *,
    channel: str | None = None,
    experiment_name: str | None = None,
) -> list[ExperimentResult]:
    """Читает один bulk summary.csv в список ExperimentResult."""
    channel = channel or "unknown"
    experiment_name = experiment_name or path.parent.name
    results: list[ExperimentResult] = []

    for row in _read_rows(path):
        if _parse_bool(row.get("skipped", "False")):
            continue

        ber = _parse_float(row.get("ber"))
        if ber is None:
            continue

        code_name = str(row.get("code_name", "")).strip()
        code_family = str(row.get("code_family", "")).strip() or parse_code_name(code_name)[0]
        n = _parse_int(row.get("n"))
        k = _parse_int(row.get("k"))
        if n is None or k is None:
            _, parsed_n, parsed_k = parse_code_name(code_name)
            n = n if n is not None else parsed_n
            k = k if k is not None else parsed_k

        results.append(
            ExperimentResult(
                experiment_name=experiment_name,
                source="bulk",
                code_family=code_family,
                family_group=family_group(code_family),
                code_name=code_name,
                decoder=str(row.get("decoder", "")).strip(),
                channel=channel,
                n=n,
                k=k,
                snr=_parse_float(row.get("ebn0_db")),
                ber=ber,
                fer=_parse_float(row.get("frame_error_rate")),
                message_count=_parse_int(row.get("message_count")),
                total_bits=_parse_int(row.get("total_bits")),
                syndrome_t=_parse_int(row.get("syndrome_t")),
            )
        )

    return results


def load_bulk_directory(bulk_root: Path) -> tuple[list[ExperimentResult], list[str], list[str]]:
    """Находит все summary.csv под bulk_root (например five_families_channels)."""
    results: list[ExperimentResult] = []
    files: list[str] = []
    warnings: list[str] = []

    if not bulk_root.is_dir():
        warnings.append(f"Каталог большого эксперимента не найден: {bulk_root}")
        return results, files, warnings

    for path in sorted(bulk_root.rglob("summary.csv")):
        if "_scratch" in path.parts:
            continue
        # Бэкапы старого прогона (64_32_100k_t4_backup) — дубли той же
        # выборки на перекрывающейся сетке Eb/N0, в анализ не входят.
        if "_backup" in str(path):
            continue
        # Каталоги быстрых 1K-прогонов отсекаем: у них другая выборка
        # (1000 слов вместо 20000), и их нельзя смешивать с 20K.
        if path.parent.name.endswith("_1k"):
            continue
        # .../<channel>/<size>_20k/summary.csv
        channel = path.parent.parent.name if len(path.parts) >= 2 else "unknown"
        size = path.parent.name
        experiment_name = f"{channel}_{size}"
        rows = load_bulk_summary(
            path, channel=channel, experiment_name=experiment_name
        )
        results.extend(rows)
        files.append(str(path))
        if not rows:
            warnings.append(f"Пустой или непригодный файл: {path}")

    if not files:
        warnings.append(f"Не найдено ни одного summary.csv в {bulk_root}")

    return results, files, warnings


def _load_t_map(csv_path: Path) -> dict[str, int]:
    """Читает {code_name: syndrome_t} из соседнего experiment_config.json."""
    cfg_path = csv_path.parent / "experiment_config.json"
    if not cfg_path.is_file():
        return {}
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    codes = cfg.get("codes")
    if not isinstance(codes, dict):
        return {}
    t_map: dict[str, int] = {}
    for name, meta in codes.items():
        if isinstance(meta, dict) and meta.get("syndrome_max_error_weight") is not None:
            t_map[str(name)] = int(meta["syndrome_max_error_weight"])
    return t_map


def load_mc_statistics(
    path: Path, t_map: dict[str, int] | None = None
) -> list[ExperimentResult]:
    """Читает один MC-файл статистики в список ExperimentResult.

    Поддерживает и ``..._all_metrics.csv`` (строки по метрикам),
    и ``...statistics.csv`` (колонка mean_BER). syndrome_t подтягивается
    из соседнего experiment_config.json (в CSV-агрегатах колонки t нет).
    """
    t_map = t_map or {}
    rows = _read_rows(path)
    if not rows:
        return []

    fieldnames = set(rows[0].keys())
    results: list[ExperimentResult] = []

    if "metric" in fieldnames:
        # all_metrics: пивот метрик по (code, channel, decoder, parameter).
        # Каждая метрика хранит mean/std/ci_low/ci_high.
        pivot: dict[tuple, dict[str, dict[str, float]]] = {}
        for row in rows:
            key = (
                str(row.get("code", "")).strip(),
                str(row.get("channel", "")).strip(),
                str(row.get("decoder", "")).strip(),
                str(row.get("parameter", "")).strip(),
            )
            metric = str(row.get("metric", "")).strip()
            entry = {
                name: _parse_float(row.get(name))
                for name in ("mean", "std", "ci_low", "ci_high")
            }
            if entry["mean"] is not None:
                pivot.setdefault(key, {})[metric] = entry

        for (code_name, channel, decoder, parameter), metrics in pivot.items():
            ber_entry = metrics.get("ber")
            if not ber_entry or ber_entry.get("mean") is None:
                continue
            family, n, k = parse_code_name(code_name)
            fer = metrics.get("frame_error_rate", {}).get("mean")
            results.append(
                ExperimentResult(
                    experiment_name=f"mc:{path.stem}",
                    source="monte_carlo",
                    code_family=family,
                    family_group=family_group(family),
                    code_name=code_name,
                    decoder=decoder,
                    channel=channel or "unknown",
                    n=n,
                    k=k,
                    snr=_parse_float(parameter),
                    ber=ber_entry["mean"],
                    fer=fer,
                    ber_ci_low=ber_entry.get("ci_low"),
                    ber_ci_high=ber_entry.get("ci_high"),
                    syndrome_t=t_map.get(code_name),
                )
            )
        return results

    # statistics.csv: mean_BER.
    experiment_name = f"mc:{path.stem}"
    for row in rows:
        ber = _parse_float(row.get("mean_BER"))
        if ber is None:
            continue
        code_name = str(row.get("code", "")).strip()
        family, n, k = parse_code_name(code_name)
        results.append(
            ExperimentResult(
                experiment_name=experiment_name,
                source="monte_carlo",
                code_family=family,
                family_group=family_group(family),
                code_name=code_name,
                decoder=str(row.get("decoder", "")).strip(),
                channel=str(row.get("channel", "")).strip() or "unknown",
                n=n,
                k=k,
                snr=_parse_float(row.get("parameter")),
                ber=ber,
                fer=None,
                ber_ci_low=_parse_float(row.get("ci_low")),
                ber_ci_high=_parse_float(row.get("ci_high")),
                syndrome_t=t_map.get(code_name),
            )
        )
    return results


def load_mc_directory(results_root: Path) -> tuple[list[ExperimentResult], list[str], list[str]]:
    """Находит MC-файлы статистики под results_root.

    Загружаем оба формата (all_metrics и statistics), но дедуплицируем
    по эксперименту: ``X_all_metrics.csv`` и ``X.csv`` — это один и тот
    же прогон, описанный двумя файлами. Загружается только один
    (предпочтительно all_metrics, там больше метрик).
    """
    results: list[ExperimentResult] = []
    files: list[str] = []
    warnings: list[str] = []

    if not results_root.is_dir():
        warnings.append(f"Каталог Monte Carlo не найден: {results_root}")
        return results, files, warnings

    all_metrics = sorted(results_root.rglob("*_all_metrics.csv"))
    plain = sorted(results_root.rglob("wavelet_channel_decoder_statistics.csv"))

    # Нормализуем имя эксперимента: X_all_metrics -> X.
    def _experiment_key(path: Path) -> str:
        stem = path.stem
        if stem.endswith("_all_metrics"):
            stem = stem[: -len("_all_metrics")]
        return str(path.parent / stem)

    # all_metrics имеет приоритет: там есть FER и прочие метрики.
    by_key: dict[str, Path] = {}
    for path in all_metrics:
        by_key[_experiment_key(path)] = path
    for path in plain:
        key = _experiment_key(path)
        if key not in by_key:
            by_key[key] = path

    candidates = [by_key[k] for k in sorted(by_key)]

    for path in candidates:
        if "_scratch" in path.parts:
            continue
        rows = load_mc_statistics(path, _load_t_map(path))
        results.extend(rows)
        files.append(str(path))
        if not rows:
            warnings.append(f"Пустой или непригодный MC-файл: {path}")

    if not files:
        warnings.append(
            f"Не найдено MC-файлов статистики в {results_root} "
            "(ожидались results/** или research/results/** "
            "wavelet_channel_decoder_statistics*.csv)"
        )

    return results, files, warnings


def load_all(
    bulk_root: str | Path = "research_results/five_families_channels",
    results_root: str | Path = "results",
) -> LoadedData:
    """Загружает bulk и Monte Carlo результаты.

    MC-файлы ищутся в ``results_root``. Если ``results_root`` является
    ``results`` (или аналогичным), автоматически также проверяется
    ``research/results`` как fallback.
    """

    bulk_rows, bulk_files, bulk_warnings = load_bulk_directory(
        Path(bulk_root)
    )

    mc_rows = []
    mc_files = []
    mc_warnings = []

    mc_roots: list[Path] = [Path(results_root)]
    # Автоматически добавляем research/results как fallback, если
    # results_root выглядит как корень проекта/результатов.
    results_path = Path(results_root)
    if str(results_path) in {"results", "research/results"}:
        if str(results_path) != "research/results":
            mc_roots.append(Path("research/results"))

    all_mc_warnings: list[str] = []
    for root in mc_roots:
        rows, files, warnings = load_mc_directory(root)

        mc_rows.extend(rows)
        mc_files.extend(files)

        # Предупреждения запоминаем, но добавим только если вообще ничего не найдено.
        all_mc_warnings.extend(warnings)

    # Добавляем предупреждения только если MC-файлы совсем не найдены.
    if not mc_files:
        mc_warnings.extend(all_mc_warnings)

    print()
    print("=== REPORTER SOURCES ===")

    print("BULK:")
    for f in bulk_files:
        print(" ", f)

    print("MC:")
    for f in mc_files:
        print(" ", f)

    print("========================")
    print()

    return LoadedData(
        results=bulk_rows + mc_rows,
        bulk_files=bulk_files,
        mc_files=mc_files,
        warnings=bulk_warnings + mc_warnings,
    )
