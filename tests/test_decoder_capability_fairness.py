"""Корректирующая способность в MC-эксперименте должна быть одинаковой
внутри группы размерности.

Правило: если один код способен исправлять 5 ошибок, а остальные только 3,
то ограничиваем ВСЕХ значением 3. Иначе сравнение измеряет настройку
декодера, а не качество кода.

Проверяем и syndrome_max_error_weight, и ёмкость chase
(inner_t + p), поскольку именно она определяет, сколько ошибок
алгоритм Чейза реально исправляет.

t выбран равным min(floor((d_min-1)/2)) по семействам группы, поэтому
ни один код не исправляет детерминированно неисправимую ошибку и
miscorrection_rate сопоставим между семействами.
"""

from __future__ import annotations

import pytest

from research.run_wavelet_channel_decoder_experiment import CODE_CONFIGS

# размерность -> ожидаемое общее значение t
EXPECTED_T = {16: 2, 32: 3, 64: 4}

# размерность -> ожидаемая ёмкость chase (inner_t + p)
EXPECTED_CHASE_CAP = {16: 5, 32: 7, 64: 9}

FAMILIES = {"wavelet", "bch_derived", "goppa_derived", "reed_solomon_binary", "ldpc"}


def _codes_by_n():
    by_n: dict[int, list] = {}
    for config in CODE_CONFIGS.values():
        by_n.setdefault(config.n, []).append(config)
    return by_n


def test_mc_covers_all_five_families_per_size() -> None:
    """В каждой размерности участвуют все 5 семейств."""
    by_n = _codes_by_n()
    assert set(by_n) == {16, 32, 64}
    for n, codes in by_n.items():
        assert {c.family for c in codes} == FAMILIES, (
            f"n={n}: нет всех 5 семейств, получено {sorted({c.family for c in codes})}"
        )


@pytest.mark.parametrize("n", [16, 32, 64])
def test_syndrome_t_is_uniform_within_size(n: int) -> None:
    """Все коды одной размерности используют одинаковый t."""
    codes = _codes_by_n()[n]
    t_values = {c.syndrome_max_error_weight for c in codes}
    assert len(t_values) == 1, (
        f"n={n}: неодинаковый syndrome t {t_values} "
        f"({[(c.name, c.syndrome_max_error_weight) for c in codes]})"
    )
    assert t_values == {EXPECTED_T[n]}, (
        f"n={n}: ожидался общий t={EXPECTED_T[n]}, получено {t_values}"
    )


@pytest.mark.parametrize("n", [16, 32, 64])
def test_chase_capacity_is_uniform_within_size(n: int) -> None:
    """Ёмкость chase (inner_t + p) одинакова для всех кодов размерности."""
    codes = _codes_by_n()[n]
    caps = {
        c.name: c.chase_inner_decoder_max_error_weight
        + c.chase_unreliable_positions_count
        for c in codes
    }
    assert len(set(caps.values())) == 1, (
        f"n={n}: неодинаковая ёмкость chase {caps}"
    )
    assert set(caps.values()) == {EXPECTED_CHASE_CAP[n]}, (
        f"n={n}: ожидалась ёмкость chase={EXPECTED_CHASE_CAP[n]}, "
        f"получено {caps}"
    )


@pytest.mark.parametrize("n", [16, 32, 64])
def test_chase_inner_t_matches_group_t(n: int) -> None:
    """Внутренний декодер chase настроен на общий t группы."""
    codes = _codes_by_n()[n]
    inner = {c.chase_inner_decoder_max_error_weight for c in codes}
    assert inner == {EXPECTED_T[n]}, (
        f"n={n}: chase inner_t должен совпадать с общим t={EXPECTED_T[n]}, "
        f"получено {inner}"
    )


@pytest.mark.parametrize("n", [16, 32, 64])
def test_no_code_decodes_beyond_its_own_distance(n: int) -> None:
    """t не превышает гарантированный радиус floor((d_min-1)/2) НИ У ОДНОГО кода.

    Иначе синдромный декодер детерминированно «исправляет» неисправимую
    ошибку в другую кодовую форму, и miscorrection_rate такого кода
    несопоставим с остальными: он штрафует не за качество кода,
    а за слишком сильный декодер.
    """
    codes = _codes_by_n()[n]
    t = EXPECTED_T[n]
    over = []
    for c in codes:
        d = c.minimum_distance_exact or c.minimum_distance_lower_bound
        assert d is not None, f"{c.name}: не задан d_min, проверить радиус нельзя"
        radius = (d - 1) // 2
        if t > radius:
            over.append(f"{c.name} (d={d}, radius={radius}, t={t})")
    assert not over, (
        f"n={n}: t={t} превышает гарантированный радиус у {over}"
    )


@pytest.mark.parametrize("n", [16, 32, 64])
def test_t_equals_min_radius_of_group(n: int) -> None:
    """Общий t равен min(radius) по семействам группы, а не больше."""
    codes = _codes_by_n()[n]
    per_code = {}
    for c in codes:
        d = c.minimum_distance_exact or c.minimum_distance_lower_bound
        assert d is not None, f"{c.name}: не задан d_min"
        per_code[c.name] = (d - 1) // 2
    assert EXPECTED_T[n] == min(per_code.values()), (
        f"n={n}: t={EXPECTED_T[n]} != min(radius)={min(per_code.values())}; "
        f"radius по кодам: {per_code}"
    )
