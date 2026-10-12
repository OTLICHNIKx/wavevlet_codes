#!/usr/bin/env python3
"""
Полный прогон: 5 кодов × 3 размера × 3 канала × 4 декодера × 100k слов.
Сохраняет результаты в research_results/five_families_full_100k/
"""

import sys
import dataclasses
import json
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from research.config import _load_preset
from research.runner import run_research

# === КОНФИГУРАЦИЯ ===
N = 100_000  # слов на одну точку Eb/N0
EBN0_VALUES = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
SIZES = [("16_8", 16, 8), ("32_16", 32, 16), ("64_32", 64, 32)]
CHANNELS = ["rayleigh", "rayleigh_awgn", "sinusoidal"]
# В пресетах AWGN-канал не имеет суффикса, например FIVE_FAMILIES_1K_FULL_DECODERS_16_8
# но для чистоты используем 3 канала

# Декодеры: запускаем все 4
DECODER_FLAGS = {
    "run_syndrome": True,
    "run_hard_mld": True,
    "run_soft_mld": True,
    "run_chase": True,
}

OUTPUT_ROOT = Path("research_results/five_families_full_100k")
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

print(f"Запуск полного эксперимента: 5 кодов × 3 размера × 3 канала = 45 конфигураций")
print(f"N = {N:,} слов на точку Eb/N0")
print(f"Декодеры: {', '.join(k for k,v in DECODER_FLAGS.items() if v)}")
print(f"Выход: {OUTPUT_ROOT}")
print()

for size_name, n, k in SIZES:
    for channel in CHANNELS:
        # Имя пресета зависит от канала
        if channel == "rayleigh":
            channel_suffix = "RAYLEIGH"
        elif channel == "rayleigh_awgn":
            channel_suffix = "RAYLEIGH_AWGN"
        elif channel == "sinusoidal":
            channel_suffix = "SINUSOIDAL"
        else:
            continue

        preset_name = f"FIVE_FAMILIES_1K_FULL_DECODERS_{size_name}_{channel_suffix}"

        try:
            cfg = _load_preset(preset_name)
        except Exception as e:
            print(f"[SKIP] {preset_name}: {e}")
            continue

        # Настраиваем декодеры
        dec = cfg.decoders
        dec = dataclasses.replace(dec, **DECODER_FLAGS)
        # MLD ограничен max_k_for_mld=16, при 64_32 (k=32) не запустится — это нормально

        # Настраиваем эксперимент
        cfg = dataclasses.replace(
            cfg,
            message_count=N,
            decoders=dec,
            ebn0_db_values=EBN0_VALUES,
            results_dir=str(OUTPUT_ROOT / f"{channel}/{size_name}_{N//1000}k"),
        )

        print(f"\n{'='*70}")
        print(f"  {preset_name}  ->  {cfg.results_dir}")
        print(f"{'='*70}")

        try:
            rows = run_research(cfg)
            print(f"  Готово: {len(rows)} строк результатов")
        except Exception as e:
            print(f"  ОШИБКА: {e}")
            import traceback
            traceback.print_exc()

print(f"\nВсе конфигурации обработаны. Результаты в {OUTPUT_ROOT}")