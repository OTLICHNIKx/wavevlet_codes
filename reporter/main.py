"""Точка входа модуля reporter.

Запуск::

    python -m reporter
    python -m reporter --bulk-root research_results/five_families_channels \
        --results-root results --output reporter/output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import analyze
from .loader import load_all
from .report_generator import write_report
from .visualization import generate_all


DEFAULT_BULK_ROOT = "research_results/five_families_channels"
DEFAULT_RESULTS_ROOT = "results"
DEFAULT_OUTPUT = "reporter/output"
REPORT_NAME = "wavelet_advantage_report.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reporter",
        description=(
            "Анализ преимуществ Wavelet-кодов по готовым CSV-результатам "
            "экспериментов. Не пересчитывает симуляции."
        ),
    )
    parser.add_argument(
        "--bulk-root",
        default=DEFAULT_BULK_ROOT,
        help="Каталог большого эксперимента (по умолчанию %(default)s)",
    )
    parser.add_argument(
        "--results-root",
        default=DEFAULT_RESULTS_ROOT,
        help="Каталог Monte Carlo результатов (по умолчанию %(default)s)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Каталог для отчёта и графиков (по умолчанию %(default)s)",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Не генерировать графики",
    )
    return parser


def run(
    bulk_root: str | Path = DEFAULT_BULK_ROOT,
    results_root: str | Path = DEFAULT_RESULTS_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT,
    *,
    make_plots: bool = True,
) -> int:
    """Основной сценарий. Возвращает exit code."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("reporter: загрузка результатов...")
    data = load_all(bulk_root, results_root)
    print(
        f"reporter: bulk-файлов {len(data.bulk_files)}, "
        f"MC-файлов {len(data.mc_files)}, "
        f"точек результатов {len(data.results)}"
    )
    for warning in data.warnings:
        print(f"reporter: предупреждение: {warning}")

    print("reporter: анализ...")
    analysis = analyze(data)
    print(
        f"reporter: сравнений {analysis.total_points}, "
        f"побед Wavelet {analysis.win_points}, "
        f"зон доминирования {len(analysis.zones)}"
    )

    report_path = output_path / REPORT_NAME
    write_report(data, analysis, report_path)
    print(f"reporter: отчёт записан: {report_path}")

    if make_plots:
        created = generate_all(data, analysis, output_path)
        print(f"reporter: графиков создано: {len(created)}")
        for path in created:
            print(f"  {path}")

    if analysis.total_points == 0:
        print(
            "reporter: недостаточно данных для содержательного анализа "
            "(см. предупреждения выше)."
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(
        bulk_root=args.bulk_root,
        results_root=args.results_root,
        output_dir=args.output,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    sys.exit(main())
