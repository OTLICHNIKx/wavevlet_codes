"""Утилиты безопасности: slug, нормализация путей."""

import re
import uuid
from pathlib import Path

from app.core.config import RESULTS_ROOT, WEB_RESULTS_SUBDIR


_SLUG_RE = re.compile(r"[^a-zA-Z0-9_\-]+")


def make_slug(text: str, fallback: str = "experiment") -> str:
    """Безопасный slug для имени каталога."""
    slug = _SLUG_RE.sub("_", text.strip())[:64].strip("_")
    return slug or fallback


def make_results_dir(
    experiment_id: uuid.UUID,
    name: str,
    subdir: str = WEB_RESULTS_SUBDIR,
) -> str:
    """
    Строит безопасный каталог для результатов:

        <RESULTS_ROOT>/<subdir>/<uuid>_<slug>/

    По умолчанию subdir = "web" (локальные рассчёты), для импорта
    используется IMPORTED_RESULTS_SUBDIR.

    Пользовательский ввод не может выйти за пределы RESULTS_ROOT.
    """
    slug = make_slug(name)
    rel = f"{subdir}/{experiment_id.hex[:12]}_{slug}"
    abs_path = (RESULTS_ROOT / rel).resolve()

    # Защита от path traversal: каталог обязан быть внутри RESULTS_ROOT.
    if not abs_path.is_relative_to(RESULTS_ROOT):
        raise ValueError("Недопустимый путь результатов")

    return str(abs_path)


def resolve_results_dir(stored_path: str) -> Path:
    """Преобразует сохранённый host/Docker путь в текущий RESULTS_ROOT."""
    direct = Path(stored_path).resolve()
    if direct.is_relative_to(RESULTS_ROOT):
        return direct
    # Внутренние reader-тесты и локальные аналитические вызовы могут
    # передавать уже существующий временный каталог напрямую.
    if direct.is_dir() and (direct / "summary.csv").is_file():
        return direct

    portable = stored_path.replace("\\", "/")
    marker = "/research_results/"
    if marker not in portable:
        raise ValueError("Недопустимый путь результатов")

    relative = portable.split(marker, 1)[1]
    resolved = (RESULTS_ROOT / relative).resolve()
    if not resolved.is_relative_to(RESULTS_ROOT):
        raise ValueError("Недопустимый путь результатов")
    return resolved
