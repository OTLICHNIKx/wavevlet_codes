# Архив one-shot скриптов

Исторические скрипты одноразовых поисков и проверок. Сохранены для
воспроизводимости результатов исследования; в активный пайплайн не
используются и могут не запускаться на текущей версии кода.

| Скрипт | Назначение | Артефакты |
|---|---|---|
| `find_best_bch_16_8.py`, `find_best_bch_16_8_v2.py` | Поиск оптимальных puncture-пар для BCH-derived [16,8] | `research_results/code_optimization/bch_32_16_*`, пресеты `BCH_DERIVED_16_8_*` |
| `find_valid_bch_like_h_64_32.py`, `bch_like_h.py` | Генерация BCH-подобной матрицы h для wavelet [64,32] | `research/run_compare_64_32_h.py` (BASELINE_BCH_LIKE_H_64_32) |
| `find_ldpc_presets.py` | Поиск и ремонт QC-LDPC матриц для [16,8]/[32,16]/[64,32] | `ldpc/presets.py` |
| `check_64_32_error_radius.py`, `check_min_distance_64_32.py` | Анализ d_min и радиуса коррекции [64,32] | метаданные distance в пресетах |
| `check_bch_16_8_final.py`, `check_compact_syndrome_table_64_32.py` | Финальные проверки семейств | логи в `research_results/` |
| `check_curator_coefficients.py`, `check_min_distance_64_32.py` | Сломаны ещё до архива: импортируют несуществующий `research.runner.build_code_from_config` | - |
| `test_research.py`, `test_research_metrics.py`, `test_research_wrappers.py` | Ранние smoke-скрипты (не pytest: нет assert) | - |
| `run_bch_smoke.py`, `run_compare_*_smoke.py`, `run_preliminary_comparison.py`, `run_research_10000.py` | Ранние smoke-прогоны, заменены пресетами `*_SMOKE_CONFIG` + `run_from_json.py` | `research_results/` |
