"""Manual 20K four-family full-decoder comparison runner.
Run explicitly by the user; this module is intentionally not executed by tests."""
from __future__ import annotations

import argparse

from research.config import (
    FOUR_FAMILIES_20K_FULL_DECODERS_16_8,
    FOUR_FAMILIES_20K_FULL_DECODERS_32_16,
    FOUR_FAMILIES_20K_FULL_DECODERS_64_32,
)
from research.runner import run_research

CONFIGS = {
    "16_8": FOUR_FAMILIES_20K_FULL_DECODERS_16_8,
    "32_16": FOUR_FAMILIES_20K_FULL_DECODERS_32_16,
    "64_32": FOUR_FAMILIES_20K_FULL_DECODERS_64_32,
}


def run_size(size: str) -> None:
    config = CONFIGS[size]
    print(f"Running manual 20K comparison for [{size.replace(chr(95), chr(44))}] with 4 families")
    rows = run_research(config)
    print(f"Completed {len(rows)} rows; results_dir={config.results_dir}")
    for row in rows:
        print(row["code_name"], row["code_family"], row["decoder"], row["ebn0_db"], row["ber"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run prepared four-family 20K comparison")
    parser.add_argument("--size", choices=["16_8", "32_16", "64_32", "all"], default="all")
    args = parser.parse_args()
    sizes = list(CONFIGS) if args.size == "all" else [args.size]
    for size in sizes:
        run_size(size)


if __name__ == "__main__":
    main()
