#!/usr/bin/env python3
"""
Честный эксперимент 64/32 (вариант A): 5 семейств × 3 канала × 4 декодера.

Каждый код получает syndrome t и chase p по СВОЕМУ точному d_min:
    wavelet   d=12  -> t=5, p=6
    goppa     d=11 (deg=5, seed=9) -> t=5, p=6
    rs        d=10  -> t=4, p=5
    bch       d=9   -> t=4, p=5
    ldpc      d=9   -> t=4, p=5

N = 100 000 слов на точку Eb/N0, сетка 0–12 dB (18 точек).
Результаты ПЕРЕЗАПИСЫВАЮТ summary.csv в
    research_results/five_families_full_100k/<channel>/64_32_100k/
(старые t=4 результаты копируются в 64_32_100k_t4_backup перед прогоном).

Запуск:
    python run_fair_t_64_32.py
"""

import dataclasses
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from research.config import _load_preset
from research.runner import run_research

CHANNELS = ("rayleigh", "rayleigh_awgn", "sinusoidal")
RESULTS_ROOT = Path("research_results/five_families_full_100k")


def backup_if_exists(results_dir: Path) -> None:
    if not results_dir.is_dir():
        return
    if any(p.name == "summary.csv" for p in results_dir.glob("*.csv")):
        backup = results_dir.parent / (results_dir.name + "_t4_backup")
        if not backup.exists():
            shutil.copytree(results_dir, backup)
            print(f"  [backup] {results_dir} -> {backup}")


def main() -> None:
    print("Честный эксперимент: 5 кодов × 3 канала × 4 декодера × 100k слов (64/32)")
    print("t=5 для wavelet/goppa, t=4 для rs/bch/ldpc, Eb/N0: 0..12 dB (18 точек)")
    print()

    failed = []
    for channel in CHANNELS:
        preset_name = f"FIVE_FAMILIES_64_32_FAIR_T_{channel.upper()}"
        try:
            cfg = _load_preset(preset_name)
        except Exception as exc:
            print(f"[SKIP] {preset_name}: {exc}")
            failed.append(channel)
            continue

        results_dir = Path(cfg.results_dir)
        backup_if_exists(results_dir)

        print(f"{'=' * 70}")
        print(f"  {preset_name}  ->  {results_dir}")
        print(f"{'=' * 70}")
        start = time.perf_counter()
        try:
            rows = run_research(cfg)
            print(
                f"  Готово: {len(rows)} строк за "
                f"{time.perf_counter() - start:.0f}s -> {results_dir}/summary.csv"
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            print(f"  ОШИБКА: {exc}")
            failed.append(channel)

    print()
    if failed:
        print(f"Завершено с ошибками по каналам: {failed}")
        sys.exit(1)
    print(f"Все каналы обработаны. Результаты в {RESULTS_ROOT}/<channel>/64_32_100k/")


if __name__ == "__main__":
    main()
