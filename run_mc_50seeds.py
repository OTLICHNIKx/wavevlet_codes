#!/usr/bin/env python3
"""
Монте-Карло эксперимент: 5 кодов × 3 канала × 4 декодера × 50 сидов × 1k слов.

Запуск:
    python run_mc_50seeds.py

Использует research/run_wavelet_channel_decoder_experiment.py с mode=full
(50 сидов, 1000 слов/сийд, Eb/N0 grid: 0,1,2,3,4,5,6 dB).
Все 4 декодера: syndrome, chase, hard_mld, soft_mld.
MLD для (64,32) автоматически skipped (k=32 > max_k_for_mld=16).

Результаты: research_results/mc_full_50seeds/
    - wavelet_channel_decoder_statistics.csv
    - wavelet_channel_decoder_statistics_all_metrics.csv
    - plots/*.png
    - experiment_config.json
    - experiment_log.txt
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import research.run_wavelet_channel_decoder_experiment as mc

# Перенаправляем выход в отдельный каталог
mc.RESULTS_DIR = _ROOT / "research_results" / "mc_full_50seeds"
mc.PLOTS_DIR = mc.RESULTS_DIR / "plots"
mc.CSV_PATH = mc.RESULTS_DIR / "wavelet_channel_decoder_statistics.csv"
mc.CONFIG_PATH = mc.RESULTS_DIR / "experiment_config.json"
mc.LOG_PATH = mc.RESULTS_DIR / "experiment_log.txt"

# Полный режим: 50 сидов × 1000 слов
settings = mc.ExperimentSettings(
    mode="full",
    num_seeds=50,
    words_per_seed=1000,
    ebn0_db_values=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
    channels=("rayleigh", "rayleigh_awgn", "sinusoidal"),
    decoders=("syndrome", "chase", "hard_mld", "soft_mld"),
    codes=mc.CODES,
)

if __name__ == "__main__":
    print(f"MC эксперимент: 5 кодов × 3 канала × 4 декодера")
    print(f"Сидов: {settings.num_seeds}, слов/сийд: {settings.words_per_seed}")
    print(f"Выход: {mc.RESULTS_DIR}")
    print()
    mc.main(settings)
