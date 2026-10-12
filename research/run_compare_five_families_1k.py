"""Быстрый 1K five-family runner: те же условия, что и 20K, но 1000 слов.

Отличается от research/run_compare_five_families_20k.py только числом
сообщений (1000 вместо 20000) и каталогом результатов, поэтому
результаты 20K не затираются.  Используется для быстрой проверки
настроек и отладки перед полным прогоном.

Примеры:
    python -m research.run_compare_five_families_1k
    python -m research.run_compare_five_families_1k --size 32_16
"""
from __future__ import annotations

import argparse

from research.config import (
    FIVE_FAMILIES_1K_FULL_DECODERS_16_8,
    FIVE_FAMILIES_1K_FULL_DECODERS_32_16,
    FIVE_FAMILIES_1K_FULL_DECODERS_64_32,
)
from research.runner import run_research

CONFIGS = {
    "16_8": FIVE_FAMILIES_1K_FULL_DECODERS_16_8,
    "32_16": FIVE_FAMILIES_1K_FULL_DECODERS_32_16,
    "64_32": FIVE_FAMILIES_1K_FULL_DECODERS_64_32,
}


def run_size(size: str) -> None:
    config = CONFIGS[size]
    print(
        f"Running 1K five-family comparison for "
        f"[{size.replace(chr(95), chr(46))}] "
        f"(count={config.message_count}, t={config.decoders.syndrome_max_error_weight})"
    )
    rows = run_research(config)
    print(f"Completed {len(rows)} rows; results_dir={config.results_dir}")
    for row in rows:
        print(
            row["code_name"],
            row["code_family"],
            row["decoder"],
            row["ebn0_db"],
            row["ber"],
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run 1K five-family comparison (quick check)"
    )
    parser.add_argument(
        "--size", choices=["16_8", "32_16", "64_32", "all"], default="all"
    )
    args = parser.parse_args()
    sizes = list(CONFIGS) if args.size == "all" else [args.size]
    for size in sizes:
        run_size(size)


if __name__ == "__main__":
    main()
