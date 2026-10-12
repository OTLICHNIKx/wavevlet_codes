"""Извлекает «голый» ResearchConfig из файла пресета.

Файлы research/presets/experiments/*.json хранят обёртку
``{"preset": ..., "experiment": ...}``, а ``research.run_from_json``
ожидает сам объект конфига. Модуль используется скриптами запуска,
чтобы не собирать JSON в оболочке.

    python -m research.extract_preset_config \
        --preset FIVE_FAMILIES_20K_FULL_DECODERS_16_8_RAYLEIGH \
        --out runtime_config.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PRESETS_DIR = Path(__file__).resolve().parent / "presets" / "experiments"


def extract(preset: str, out: Path) -> None:
    source = PRESETS_DIR / f"{preset}.json"
    if not source.is_file():
        raise FileNotFoundError(f"Пресет не найден: {source}")

    payload = json.loads(source.read_text(encoding="utf-8"))
    config = payload.get("experiment", payload)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    extract(args.preset, args.out)
    print(f"config: {args.out}")


if __name__ == "__main__":
    main()
