"""Корректирующая способность в five-families пресетах должна быть
одинаковой внутри размерности — и в 20K, и в 1K, и во всех каналах.

Смысл: если один код исправляет 5 ошибок, а остальные только 3, то
сравнение измеряет настройку декодера, а не качество кода. Поэтому
внутри группы все коды получают одинаковые t и одинаковую ёмкость
chase (inner_t + p).

Настройки, общие для MC- и bulk-экспериментов:
    16,8  -> t=2, chase(2,3), cap 5
    32,16 -> t=3, chase(3,4), cap 7
    64,32 -> t=4, chase(4,5), cap 9

``t`` равен min(floor((d_min-1)/2)) по семействам группы, поэтому ни один
код не исправляет детерминированно неисправимую ошибку: иначе
``miscorrection_rate`` штрафовал бы за настройку декодера, а не за
качество кода.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.config import _load_preset

EXP_DIR = Path("research/presets/experiments")

SIZES = ("16_8", "32_16", "64_32")
CHANNELS = ("", "rayleigh", "rayleigh_awgn", "sinusoidal")
WORDS = ("1K", "20K")

EXPECTED = {16: (2, 2, 3), 32: (3, 3, 4), 64: (4, 4, 5)}

FAMILIES = {
    "wavelet",
    "bch_derived",
    "goppa_derived",
    "reed_solomon_binary",
    "ldpc",
}


def preset_name(words: str, size: str, channel: str) -> str:
    return (
        f"FIVE_FAMILIES_{words}_FULL_DECODERS_{size}"
        + (f"_{channel}" if channel else "")
    )


def all_preset_names() -> list[str]:
    return [
        preset_name(w, s, c)
        for w in WORDS
        for s in SIZES
        for c in CHANNELS
    ]


@pytest.mark.parametrize("name", all_preset_names())
def test_preset_file_exists(name: str) -> None:
    assert (EXP_DIR / f"{name}.json").exists(), f"нет файла пресета {name}"


@pytest.mark.parametrize("name", all_preset_names())
def test_decoder_params_uniform_within_size(name: str) -> None:
    config = _load_preset(name)
    n = config.codes[0].n
    expected = EXPECTED[n]
    actual = {
        (
            c.syndrome_max_error_weight,
            c.chase_inner_decoder_max_error_weight,
            c.chase_unreliable_positions_count,
        )
        for c in config.codes
    }
    assert actual == {expected}, (
        f"{name}: настройки декодера не выровнены: {actual}, ожидалось {expected}"
    )


@pytest.mark.parametrize("name", all_preset_names())
def test_t_never_exceeds_any_code_radius(name: str) -> None:
    """Ни один код группы не декодирует дальше своего floor((d_min-1)/2).

    Иначе miscorrection_rate такого кода несопоставим с остальными.
    """
    config = _load_preset(name)
    t = config.codes[0].syndrome_max_error_weight
    over = []
    radii = {}
    for c in config.codes:
        d = c.minimum_distance_exact or c.minimum_distance_lower_bound
        assert d is not None, f"{name}/{c.name}: не задан d_min"
        radius = (d - 1) // 2
        radii[c.name] = radius
        if t > radius:
            over.append(f"{c.name} (d={d}, radius={radius}, t={t})")
    assert not over, f"{name}: t={t} превышает радиус у {over}; radii={radii}"


@pytest.mark.parametrize("name", all_preset_names())
def test_t_equals_min_radius_of_group(name: str) -> None:
    """t равен min(radius) по кодам группы, а не больше."""
    config = _load_preset(name)
    t = config.codes[0].syndrome_max_error_weight
    radii = [
        ((c.minimum_distance_exact or c.minimum_distance_lower_bound) - 1) // 2
        for c in config.codes
    ]
    assert t == min(radii), (
        f"{name}: t={t} != min(radius)={min(radii)}; radii={radii}"
    )


@pytest.mark.parametrize("name", all_preset_names())
def test_all_five_families_present(name: str) -> None:
    config = _load_preset(name)
    assert len(config.codes) == 5
    assert {c.family for c in config.codes} == FAMILIES


@pytest.mark.parametrize("name", all_preset_names())
def test_message_count_matches_word_budget(name: str) -> None:
    config = _load_preset(name)
    expected_count = 1000 if "_1K_" in name else 20000
    assert config.message_count == expected_count


def test_1k_and_20k_use_different_results_dirs() -> None:
    """Прогон 1K не должен затирать результаты 20K."""
    for size in SIZES:
        for channel in CHANNELS:
            one_k = _load_preset(preset_name("1K", size, channel)).results_dir
            twenty_k = _load_preset(preset_name("20K", size, channel)).results_dir
            assert one_k != twenty_k, (
                f"{size}/{channel or 'awgn'}: 1K и 20K пишут в один каталог {one_k}"
            )
            assert one_k.endswith("_1k"), one_k
            assert twenty_k.endswith("_20k"), twenty_k


def test_bulk_and_mc_share_decoder_settings() -> None:
    """20K/1K пресеты и MC-коды используют одинаковые t и chase."""
    from research.run_wavelet_channel_decoder_experiment import CODE_CONFIGS

    mc_by_n: dict[int, tuple[int, int, int]] = {}
    for config in CODE_CONFIGS.values():
        value = (
            config.syndrome_max_error_weight,
            config.chase_inner_decoder_max_error_weight,
            config.chase_unreliable_positions_count,
        )
        mc_by_n.setdefault(config.n, value)
        assert mc_by_n[config.n] == value, (
            f"MC: n={config.n} не выровнен: {mc_by_n[config.n]} vs {value}"
        )

    for n, expected in mc_by_n.items():
        assert expected == EXPECTED[n], (
            f"MC n={n}: {expected} не совпадает с общим {EXPECTED[n]}"
        )

    for words in WORDS:
        for size in SIZES:
            config = _load_preset(preset_name(words, size, ""))
            assert config.codes[0].n in mc_by_n
