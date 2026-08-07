"""Запуск исследования из JSON-файла конфигурации.

Используется веб-интерфейсом для запуска экспериментов в отдельном
процессе. Выводит в stdout структурированные сообщения прогресса
в формате:

    PROGRESS {"stage": "...", ...}

Весь остальное -- обычный stdout runner'а (логи).
"""

import argparse
import json
import sys
import traceback


def _emit_progress(payload: dict) -> None:
    """Выводит одну строку прогресса и немедленно сбрасывает буфер."""
    print(f"PROGRESS {json.dumps(payload, ensure_ascii=False)}", flush=True)


def run_with_progress(config_json_path: str) -> int:
    """Загружает конфиг, запускает исследование, возвращает exit code."""

    # Импорты здесь, чтобы вся тяжёлая инициализация (numpy и т.п.)
    # происходила уже внутри дочернего процесса, а не при --help.
    from research.config import ResearchConfig
    from research.runner import run_research

    try:
        config = ResearchConfig.load_json(config_json_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        _emit_progress(
            {
                "stage": "failed",
                "error": f"Не удалось загрузить конфигурацию: {exc}",
            }
        )
        return 2

    workload = config.estimate_workload()

    _emit_progress(
        {
            "stage": "started",
            "codes": [c.name for c in config.codes],
            "ebn0_db_values": list(config.ebn0_db_values),
            "message_count": config.message_count,
            **workload,
        }
    )

    try:
        results_dir = config.results_dir
        run_research(config, progress_callback=_emit_progress)

        _emit_progress(
            {
                "stage": "completed",
                "results_dir": str(results_dir),
            }
        )
        return 0

    except KeyboardInterrupt:
        _emit_progress({"stage": "interrupted"})
        return 130

    except Exception as exc:  # noqa: BLE001 -- здесь ловим всё
        _emit_progress(
            {
                "stage": "failed",
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        )
        traceback.print_exc()
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Запуск исследования из JSON-конфигурации",
    )
    parser.add_argument("config_path", help="Путь к JSON-файлу конфигурации")
    args = parser.parse_args()

    exit_code = run_with_progress(args.config_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
