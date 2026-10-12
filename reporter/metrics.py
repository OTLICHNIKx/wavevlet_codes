"""Расчёт метрик преимущества Wavelet над конкурентами."""

from __future__ import annotations

import statistics
from collections import defaultdict

from .models import (
    FAMILY_LABELS,
    MIN_REL_GAIN,
    SIGNIFICANCE_Z,
    ComparisonPoint,
    ExperimentResult,
    FamilySummary,
    WAVELET_GROUP,
)


# Считаем BER-точку значимой, если она не нулевая: gain к нулевому BER
# не определён (бесконечный выигрыш), такие точки помечаем отдельно.
def ber_gain(wavelet_ber: float, other_ber: float) -> float:
    """gain = BER_other / BER_wavelet.

    Возвращает ``inf``, если Wavelet имеет нулевой BER при ненулевом
    у конкурента. Обе нулевые точки gain не имеют (возвращается NaN
    через ValueError) — вызывающий код должен отфильтровать.
    """
    if wavelet_ber <= 0.0 and other_ber <= 0.0:
        raise ValueError("gain undefined for two zero BER points")
    if wavelet_ber <= 0.0:
        return float("inf")
    return other_ber / wavelet_ber


def _binomial_sigma(ber: float, total_bits: int | None) -> float | None:
    """Стандартное отклонение биномиальной оценки BER."""
    if total_bits is None or total_bits <= 0 or ber < 0.0 or ber > 1.0:
        return None
    import math

    return math.sqrt(ber * (1.0 - ber) / total_bits)


def _ci_overlaps(
    wavelet: ExperimentResult, other: ExperimentResult
) -> bool | None:
    """Проверяет перекрытие 95% CI (None — данных недостаточно)."""
    if None in (
        wavelet.ber_ci_low,
        wavelet.ber_ci_high,
        other.ber_ci_low,
        other.ber_ci_high,
    ):
        return None
    return not (
        wavelet.ber_ci_high < other.ber_ci_low
        or other.ber_ci_high < wavelet.ber_ci_low
    )


def difference_is_significant(
    wavelet: ExperimentResult, other: ExperimentResult
) -> bool:
    """Различие BER статистически значимо.

    Критерий (любой из сработавших):
      * bulk: z-score >= SIGNIFICANCE_Z по биномиальной оценке;
      * MC: 95% CI двух кодов не пересекаются;
      * если данных для теста нет — берём MIN_REL_GAIN как нижнюю границу
        содержательности (здесь не решаем, а только проверяем CI/z).
    """
    w_ber = wavelet.ber if wavelet.ber is not None else 0.0
    o_ber = other.ber if other.ber is not None else 0.0

    # 1) z-score по total_bits (bulk).
    w_sig = _binomial_sigma(w_ber, wavelet.total_bits)
    o_sig = _binomial_sigma(o_ber, other.total_bits)
    if w_sig is not None and o_sig is not None:
        pooled = (w_sig**2 + o_sig**2) ** 0.5
        if pooled > 0.0:
            z = abs(o_ber - w_ber) / pooled
            if z >= SIGNIFICANCE_Z:
                return True
            return False

    # 2) Непересечение 95% CI (MC).
    overlaps = _ci_overlaps(wavelet, other)
    if overlaps is not None:
        return not overlaps

    # 3) Нет данных для теста — значимо только при заметном gain
    #    в любую сторону (симметричный порог содержательности).
    if w_ber <= 0.0 and o_ber <= 0.0:
        return False
    if w_ber <= 0.0 or o_ber <= 0.0:
        return True
    ratio = max(o_ber / w_ber, w_ber / o_ber)
    return ratio >= (1.0 + MIN_REL_GAIN)


def _ci_of(result: ExperimentResult) -> tuple[float, float] | None:
    if result.ber_ci_low is None or result.ber_ci_high is None:
        return None
    return (result.ber_ci_low, result.ber_ci_high)


def build_comparisons(
    results: list[ExperimentResult],
    *,
    source: str | None = None,
) -> list[ComparisonPoint]:
    """Строит попарные сравнения Wavelet vs каждый конкурент в точках.

    Точка сравнения: (experiment, channel, size, decoder, snr).
    Конкуренты без данных в этой точке просто не сравниваются.

    Трёхсторонний вердикт:
      win   — Wavelet ниже, различие значимо и gain >= 1+MIN_REL_GAIN;
      loss  — конкурент ниже, различие значимо и (обратный) gain >= 1+MIN;
      иначе — ничья (значимо не больше порога или не значимо).
    """
    # Индексация: (exp, channel, size, decoder, snr) -> {family_group: result}
    by_point: dict[tuple, dict[str, ExperimentResult]] = defaultdict(dict)

    for r in results:
        if source is not None and r.source != source:
            continue
        if r.ber is None or r.snr is None or r.n is None or r.k is None:
            continue
        if r.family_group == WAVELET_GROUP and code_is_ambiguous(r):
            continue
        key = (
            r.source,
            r.experiment_name,
            r.channel,
            r.code_size,
            r.decoder,
            r.snr,
        )
        # При равенстве группы оставляем лучший (минимальный) BER.
        current = by_point[key].get(r.family_group)
        if current is None or current.ber is None or (
            r.ber is not None and r.ber < current.ber
        ):
            by_point[key][r.family_group] = r

    points: list[ComparisonPoint] = []
    for key, families in by_point.items():
        src, experiment, channel, size, decoder, snr = key
        wavelet_result = families.get(WAVELET_GROUP)
        if wavelet_result is None or wavelet_result.ber is None:
            continue
        wavelet_ber = wavelet_result.ber
        for group, other_result in families.items():
            if group == WAVELET_GROUP or other_result.ber is None:
                continue
            other_ber = other_result.ber
            try:
                gain = ber_gain(wavelet_ber, other_ber)
            except ValueError:
                continue
            significant = difference_is_significant(
                wavelet_result, other_result
            )
            wavelet_lower = wavelet_ber < other_ber
            # Gain содержателен, если разница не меньше порога (или
            # Wavelet на нуле при ненулевом конкуренте).
            meaningful_win = wavelet_ber <= 0.0 or gain >= 1.0 + MIN_REL_GAIN
            win = wavelet_lower and significant and meaningful_win
            if other_ber <= 0.0:
                inverse_gain = float("inf") if wavelet_ber > 0.0 else 1.0
            else:
                inverse_gain = wavelet_ber / other_ber
            meaningful_loss = other_ber <= 0.0 or inverse_gain >= 1.0 + MIN_REL_GAIN
            loss = (not wavelet_lower) and significant and meaningful_loss
            points.append(
                ComparisonPoint(
                    source=src,
                    experiment_name=experiment,
                    channel=channel,
                    code_size=size,
                    decoder=decoder,
                    snr=snr,
                    competitor=group,
                    wavelet_ber=wavelet_ber,
                    competitor_ber=other_ber,
                    gain=gain,
                    win=win,
                    loss=loss,
                    significant=significant,
                    wavelet_t=wavelet_result.syndrome_t,
                    competitor_t=other_result.syndrome_t,
                    wavelet_ci=_ci_of(wavelet_result),
                    competitor_ci=_ci_of(other_result),
                )
            )
    return points


def code_is_ambiguous(result: ExperimentResult) -> bool:
    """Wavelet-строки с неясной размерностью не участвуют в сравнении."""
    return result.n is None or result.k is None


def summarize_families(points: list[ComparisonPoint]) -> dict[str, FamilySummary]:
    """Свод по каждому конкурирующему семейству."""
    grouped: dict[str, list[ComparisonPoint]] = defaultdict(list)
    for point in points:
        grouped[point.competitor].append(point)

    summaries: dict[str, FamilySummary] = {}
    for competitor, items in grouped.items():
        finite_gains = [p.gain for p in items if p.gain != float("inf")]
        wins = sum(1 for p in items if p.win)
        losses = sum(1 for p in items if p.loss)
        ties = sum(1 for p in items if not p.win and not p.loss)
        wins_eq = sum(1 for p in items if p.win and p.equal_capacity is True)
        wins_neq = sum(1 for p in items if p.win and p.equal_capacity is False)
        wins_unk = sum(1 for p in items if p.win and p.equal_capacity is None)
        summary = FamilySummary(
            competitor=competitor,
            comparisons=len(items),
            wins=wins,
            ties=ties,
            losses=losses,
            wins_equal_t=wins_eq,
            wins_unequal_t=wins_neq,
            wins_unknown_t=wins_unk,
            mean_gain=statistics.fmean(finite_gains) if finite_gains else 0.0,
            max_gain=max(finite_gains) if finite_gains else 0.0,
            median_gain=statistics.median(finite_gains) if finite_gains else 0.0,
            points=items,
        )
        summaries[competitor] = summary
    return summaries


def snr_intervals(snrs: list[float], *, tolerance: float = 1e-9) -> list[tuple[float, float]]:
    """Склеивает отсортированные SNR-точки в непрерывные интервалы."""
    unique = sorted(set(snrs))
    if not unique:
        return []

    intervals: list[tuple[float, float]] = []
    start = previous = unique[0]
    for value in unique[1:]:
        # Шаг сетки в экспериментах 0.5; допускаем пропуски только
        # при разрыве больше шага.
        if value - previous > tolerance + 0.5:
            intervals.append((start, previous))
            start = value
        previous = value
    intervals.append((start, previous))
    return intervals


def format_snr_range(interval: tuple[float, float]) -> str:
    start, end = interval

    def _fmt(value: float) -> str:
        text = f"{value:g}"
        return text

    if start == end:
        return f"{_fmt(start)} dB"
    return f"{_fmt(start)}-{_fmt(end)} dB"


def family_label(group: str) -> str:
    return FAMILY_LABELS.get(group, group)
