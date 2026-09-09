"""Восстановление phase-1 baseline.json из git HEAD (коммит 'add ldpc',
состояние production-кодов ДО фазы 1).

Причина: скрипт capture_phase2_baseline по ошибке использовал
research_results/code_optimization как директорию записи и перезаписал
phase-1 baseline.json. Конфигурация до фазы 1 детерминированно
восстанавливается из git HEAD, переснимается тем же кодом
capture_baseline.capture_code и сохраняется на место с пометкой.

Запуск (из корня репозитория):
    python research_results/code_optimization/restore_phase1_baseline.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

TARGET = Path("research_results/code_optimization/baseline.json")


def load_head_config() -> types.ModuleType:
    source = subprocess.check_output(
        ["git", "show", "HEAD:research/config.py"], text=True, encoding="utf-8"
    )
    temp = Path("research_results/code_optimization/_phase1_head_config.py")
    temp.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_phase1_head_config", temp)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["_phase1_head_config"] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    from research.optimization.capture_baseline import capture_code
    from research.optimization.common import save_json

    head = load_head_config()
    baseline = {}
    for config in (
        head.FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
        head.FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
        head.FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
    ):
        size = config.codes[0].n
        baseline[f"{size}_{size // 2}"] = [
            capture_code(code_config) for code_config in config.codes
        ]
    baseline["_restored_from"] = "git HEAD (commit 'add ldpc') via restore_phase1_baseline.py"
    path = save_json("baseline.json", baseline, directory=TARGET.parent)
    print("restored:", path)
    for size_key, entries in baseline.items():
        if size_key.startswith("_"):
            continue
        for entry in entries:
            exact = entry.get("distance_exact_enum", {}).get("d_min_exact")
            print(size_key, entry["family"], "exact=", exact, "fp=", entry["fingerprint_rref_G"])


if __name__ == "__main__":
    main()
