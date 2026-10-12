"""Аналитический модуль: где и насколько Wavelet лучше конкурентов."""

from __future__ import annotations

import statistics
from collections import defaultdict

from .metrics import (
    build_comparisons,
    family_label,
    format_snr_range,
    snr_intervals,
    summarize_families,
)
from .models import (
    AnalysisResult,
    CapacityVerdict,
    ComparisonPoint,
    LoadedData,
    LeaderboardRow,
    Zone,
)


def _ci_verdict(p: ComparisonPoint) -> str | None:
    """Вердикт по непересечению 95% CI пары точек.

    'wavelet' — CI конкурента строго выше CI wavelet (wavelet лучше);
    'other'    — наоборот; 'tie' — CI пересекаются; None — нет CI.
    """
    if not p.wavelet_ci or not p.competitor_ci:
        return None
    wl, wh = p.wavelet_ci
    ol, oh = p.competitor_ci
    if wh < ol:
        return "wavelet"
    if oh < wl:
        return "other"
    return "tie"


def _capacity_verdicts(
    points: list[ComparisonPoint],
) -> list[CapacityVerdict]:
    """CI-сводка по точкам равной ёмкости декодера (equal_t=True)."""
    grouped: dict[tuple, CapacityVerdict] = {}
    for p in points:
        if p.equal_capacity is not True:
            continue
        key = (p.channel, p.code_size, p.decoder, p.competitor)
        verdict = grouped.setdefault(
            key,
            CapacityVerdict(
                channel=p.channel,
                code_size=p.code_size,
                decoder=p.decoder,
                competitor=p.competitor,
            ),
        )
        ci = _ci_verdict(p)
        if ci is None:
            continue
        verdict.total += 1
        if ci == "wavelet":
            verdict.wavelet_wins += 1
        elif ci == "other":
            verdict.competitor_wins += 1
        else:
            verdict.ties += 1
        if p.experiment_name not in verdict.sources:
            verdict.sources = tuple(sorted({*verdict.sources, p.experiment_name}))
    return [
        grouped[key]
        for key in sorted(grouped)
        if grouped[key].total > 0
    ]


def _zones_from_points(
    points: list[ComparisonPoint],
    *,
    require_win: bool,
) -> list[Zone]:
    """Склеивает точки в зоны по (channel, size, decoder).

    require_win=True: интервал включает только SNR, где Wavelet победил
    всех конкурентов в этом (channel,size,decoder). Иначе — где победил
    хотя бы кого-то (для зон проигрыша берётся require_win=False по
    точкам с win=False).

    equal_t в зоне: True — все точки зоны при равных syndrome_t,
    False — хотя бы в одной t различаются (артефакт ёмкости декодера),
    None — t неизвестен (MC-данные).
    """
    # Группируем по (channel,size,decoder,snr) -> список точек.
    by_snr: dict[tuple[str, str, str], dict[float, list[ComparisonPoint]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for point in points:
        by_snr[(point.channel, point.code_size, point.decoder)][point.snr].append(point)

    zones: list[Zone] = []
    for (channel, size, decoder), snr_map in by_snr.items():
        winning_snrs: list[float] = []
        gains_by_snr: dict[float, list[float]] = defaultdict(list)
        competitors_by_snr: dict[float, set[str]] = defaultdict(set)
        experiments_by_snr: dict[float, set[str]] = defaultdict(set)
        flags_by_snr: dict[float, list[bool | None]] = defaultdict(list)

        for snr, items in snr_map.items():
            if require_win:
                all_win = all(p.win for p in items)
                if not all_win:
                    continue
            else:
                if not any(not p.win for p in items):
                    continue
            winning_snrs.append(snr)
            experiments_by_snr[snr] = {p.experiment_name for p in items}
            for p in items:
                if p.gain != float("inf"):
                    gains_by_snr[snr].append(p.gain)
                competitors_by_snr[snr].add(p.competitor)
                flags_by_snr[snr].append(p.equal_capacity)

        if not winning_snrs:
            continue

        for start, end in snr_intervals(winning_snrs):
            relevant_snrs = [s for s in winning_snrs if start <= s <= end]
            gains = [
                g for s in relevant_snrs for g in gains_by_snr.get(s, [])
            ]
            competitors: set[str] = set()
            experiments: set[str] = set()
            flags: list[bool | None] = []
            for s in relevant_snrs:
                competitors |= competitors_by_snr.get(s, set())
                experiments |= experiments_by_snr.get(s, set())
                flags.extend(flags_by_snr.get(s, []))
            known = [f for f in flags if f is not None]
            if not known:
                equal_t = None
            else:
                equal_t = all(known)
            zones.append(
                Zone(
                    channel=channel,
                    code_size=size,
                    decoder=decoder,
                    snr_start=start,
                    snr_end=end,
                    mean_gain=statistics.fmean(gains) if gains else 0.0,
                    competitors=tuple(sorted(competitors)),
                    experiments=tuple(sorted(experiments)),
                    equal_t=equal_t,
                )
            )
    return zones


def _leaderboard(zones: list[Zone]) -> list[LeaderboardRow]:
    rows: list[LeaderboardRow] = []
    for zone in zones:
        rows.append(
            LeaderboardRow(
                channel=zone.channel,
                code_size=zone.code_size,
                decoder=zone.decoder,
                snr_range=format_snr_range((zone.snr_start, zone.snr_end)),
                mean_gain=zone.mean_gain,
                wins=1,
                total=1,
                experiments=zone.experiments,
                equal_t=zone.equal_t,
            )
        )
    # Сначала зоны с равным t (настоящее преимущество кода), затем gain.
    rows.sort(
        key=lambda r: (
            r.equal_t is not True,
            -r.mean_gain,
        )
    )
    return rows


def _compare_mc_against_bulk(
    bulk_zones: list[Zone], mc_zones: list[Zone]
) -> tuple[list[Zone], list[Zone]]:
    """Сопоставляет MC-зоны с bulk-зонами по каналу и размеру.

    Подтверждёнными считаются MC-зоны, для которых есть bulk-зона в том
    же канале и размере с пересекающимся SNR-интервалом. Остальные MC-зоны
    помечаются как неподтверждённые (нестабильные).
    """
    bulk_index: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for zone in bulk_zones:
        bulk_index[(zone.channel, zone.code_size)].append((zone.snr_start, zone.snr_end))

    confirmed: list[Zone] = []
    unstable: list[Zone] = []
    for zone in mc_zones:
        ranges = bulk_index.get((zone.channel, zone.code_size), [])
        overlaps = any(
            zone.snr_start <= end and start <= zone.snr_end
            for start, end in ranges
        )
        (confirmed if overlaps else unstable).append(zone)
    return confirmed, unstable


def _build_conclusions(
    zones: list[Zone],
    summaries: dict,
    loss_zones: list[Zone],
) -> list[str]:
    conclusions: list[str] = []

    if zones:
        best = max(zones, key=lambda z: z.mean_gain)
        from .report_generator import _fmt_experiments
        experiment_str = _fmt_experiments(best.experiments)
        conclusions.append(
            "Wavelet показывает преимущество на канале "
            f"{best.channel} при параметрах {best.code_size} "
            f"(декодер {best.decoder}) в диапазоне SNR "
            f"{format_snr_range((best.snr_start, best.snr_end))} "
            f"со средним выигрышем BER {best.mean_gain:.2f}x "
            f"{experiment_str} "
            f"против {', '.join(family_label(c) for c in best.competitors)}."
        )
        winners = sorted(
            {family_label(c) for z in zones for c in z.competitors}
        )
        if winners:
            conclusions.append(
                "Области доминирования зафиксированы против: "
                + ", ".join(winners)
                + "."
            )
    else:
        conclusions.append(
            "Не обнаружено точек, где Wavelet выигрывает у всех конкурентов "
            "одновременно."
        )

    if summaries:
        strongest = max(
            summaries.values(),
            key=lambda s: s.mean_gain,
        )
        conclusions.append(
            f"Наибольшее среднее преимущество относительно "
            f"{family_label(strongest.competitor)}: {strongest.mean_gain:.2f}x "
            f"({strongest.wins}/{strongest.comparisons} сравнений в пользу Wavelet)."
        )

    if loss_zones:
        worst = min(loss_zones, key=lambda z: z.mean_gain)
        conclusions.append(
            "Области проигрыша: на канале "
            f"{worst.channel} при {worst.code_size} (декодер {worst.decoder}) "
            f"в диапазоне SNR {format_snr_range((worst.snr_start, worst.snr_end))} "
            "Wavelet уступает части конкурентов."
        )
    else:
        conclusions.append(
            "Явных областей устойчивого проигрыша Wavelet не обнаружено."
        )

    return conclusions


def analyze(data: LoadedData) -> AnalysisResult:
    """Полный анализ загруженных результатов."""
    result = AnalysisResult()
    result.warnings = list(data.warnings)

    points = build_comparisons(data.results)
    result.points = points
    result.family_summaries = summarize_families(points)

    if not points:
        result.conclusions = [
            "Недостаточно данных для анализа: не найдено ни одного сравнения "
            "Wavelet с конкурентами."
        ]
        return result

    win_points = [p for p in points if p.win]
    loss_points = [p for p in points if p.loss]

    zones = _zones_from_points(points, require_win=True)
    result.zones = zones
    result.leaderboard = _leaderboard(zones)

    loss_zones = _zones_from_points(loss_points, require_win=False)
    result.loss_points = loss_points

    result.capacity_verdicts = _capacity_verdicts(points)

    # MC-подтверждение: сравниваем bulk- и MC-зоны.
    bulk_points = [p for p in points if p.source == "bulk"]
    mc_points = [p for p in points if p.source == "monte_carlo"]
    bulk_win_zones = _zones_from_points(
        [p for p in bulk_points if p.win], require_win=True
    )
    mc_win_zones = _zones_from_points(
        mc_points, require_win=True
    )
    if mc_win_zones:
        confirmed, unstable = _compare_mc_against_bulk(bulk_win_zones, mc_win_zones)
    else:
        confirmed, unstable = [], []
    result.mc_confirmed = confirmed
    result.mc_unstable = unstable

    result.conclusions = _build_conclusions(zones, result.family_summaries, loss_zones)
    return result
