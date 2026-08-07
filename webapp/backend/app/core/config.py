"""Настройки backend-приложения."""

import os
from pathlib import Path


def _detect_project_root() -> Path:
    """Находит корень репозитория с кодами (там, где лежит пакет research)."""
    # webapp/backend/app/core/config.py -> подняться на 4 уровня вверх.
    here = Path(__file__).resolve()
    candidate = here.parents[4]

    # В Docker проект смонтирован в /app — переопределяем через env.
    env_root = os.environ.get("WAVELET_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()

    return candidate


PROJECT_ROOT: Path = _detect_project_root()

# Где лежат результаты исследований (volume в Docker).
RESULTS_ROOT: Path = Path(
    os.environ.get("WAVELET_RESULTS_ROOT", PROJECT_ROOT / "research_results")
).resolve()

# Данные веб-приложения (SQLite, пресеты пользователя).
WEBAPP_DATA_ROOT: Path = Path(
    os.environ.get("WAVELET_WEBAPP_DATA", PROJECT_ROOT / "webapp_data")
).resolve()

WEB_RESULTS_SUBDIR = "web"

DB_PATH: Path = WEBAPP_DATA_ROOT / "experiments.db"
PRESETS_DIR: Path = WEBAPP_DATA_ROOT / "presets"
