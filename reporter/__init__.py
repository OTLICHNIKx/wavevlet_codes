"""Модуль анализа преимуществ Wavelet-кодов.

Читает готовые CSV-результаты экспериментов (bulk-прогоны
``research_results/five_families_channels`` и Monte Carlo ``results``),
сравнивает Wavelet с остальными семействами и формирует Markdown-отчёт
с графиками.

Запуск одной командой::

    python -m reporter
"""

from .models import (
    AnalysisResult,
    ComparisonPoint,
    ExperimentResult,
    FamilySummary,
    LoadedData,
)

__all__ = [
    "AnalysisResult",
    "ComparisonPoint",
    "ExperimentResult",
    "FamilySummary",
    "LoadedData",
]
