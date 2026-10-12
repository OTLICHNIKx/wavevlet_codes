"""Запуск пресетов FIVE_FAMILIES_{20K,1K}_FULL_DECODERS для всех размерностей
и каналов одной командой.

Все эти пресеты используют одинаковые настройки корректирующей
способности внутри размерности, поэтому сравнение идёт по кодам, а не
по настройке декодера. ``t`` не превышает гарантированный радиус
floor((d_min-1)/2) ни у одного семейства, поэтому синдромный декодер
не может детерминированно исправить неисправимую ошибку и
miscorrection_rate остаётся сопоставимым между кодами:

    16,8  -> t=2 (min radius 2), chase(2,3), ёмкость 5
    32,16 -> t=2 (min radius 2, ограничен bch d=6), chase(2,5), ёмкость 7
    64,32 -> t=4 (min radius 4), chase(4,5), ёмкость 9

Примеры:
    # быстрая проверка на 1000 слов
    python -m research.run_five_families_presets --words 1k --size 32_16

    # все размерности и каналы на 20000 слов
    python -m research.run_five_families_presets --words 20k

    # только AWGN, только 64,32
    python -m research.run_five_families_presets --words 20k --channel awgn --size 64_32
"""
from __future__ import annotations

import argparse
import sys

from research.config import _load_preset
from research.runner import run_research

SIZES = ("16_8", "32_16", "64_32")
CHANNELS = ("", "rayleigh", "rayleigh_awgn", "sinusoidal")

# n -> (t, chase_inner_t, chase_p); t == min(radius) по семействам группы
EXPECTED = {16: (2, 2, 3), 32: (3, 3, 4), 64: (4, 4, 5)}


def preset_name(words: str, size: str, channel: str) -> str:
    prefix = "FIVE_FAMILIES_1K" if words == "1k" else "FIVE_FAMILIES_20K"
    return f"{prefix}_FULL_DECODERS_{size}" + (f"_{channel}" if channel else "")


def run_one(words: str, size: str, channel: str) -> bool:
    name = preset_name(words, size, channel)
    try:
        config = _load_preset(name)
    except AttributeError as exc:
        print(f"[SKIP] {name}: {exc}", flush=True)
        return False

    n = config.codes[0].n
    expected_t, expected_it, expected_p = EXPECTED[n]
    actual = {
        (c.syndrome_max_error_weight,
         c.chase_inner_decoder_max_error_weight,
         c.chase_unreliable_positions_count)
        for c in config.codes
    }
    if actual != {(expected_t, expected_it, expected_p)}:
        print(
            f"[FAIL] {name}: настройки декодера не выровнены: {actual}, "
            f"ожидалось {(expected_t, expected_it, expected_p)}",
            flush=True,
        )
        return False

    print(
        f"\n=== {name} ===\n"
        f"    count={config.message_count}  channel={config.channel_type}  "
        f"t={expected_t}  chase=({expected_it},{expected_p})  "
        f"cap={expected_it + expected_p}\n"
        f"    results_dir={config.results_dir}",
        flush=True,
    )
    rows = run_research(config)
    print(f"    готово: {len(rows)} строк", flush=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run FIVE_FAMILIES full-decoder presets"
    )
    parser.add_argument(
        "--words", choices=["1k", "20k"], default="20k",
        help="Объём выборки: 1k = 1000 слов (быстро), 20k = 20000 слов",
    )
    parser.add_argument("--size", choices=[*SIZES, "all"], default="all")
    parser.add_argument("--channel", choices=[*CHANNELS, "all"], default="all")
    args = parser.parse_args()

    sizes = list(SIZES) if args.size == "all" else [args.size]
    channels = list(CHANNELS) if args.channel == "all" else [args.channel]

    ok = 0
    failed = 0
    for size in sizes:
        for channel in channels:
            if run_one(args.words, size, channel):
                ok += 1
            else:
                failed += 1

    print(f"\nИтог: успешно {ok}, пропущено/ошибок {failed}")
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
