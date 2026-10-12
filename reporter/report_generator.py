"""Формирование Markdown-отчёта wavelet_advantage_report.md."""

from __future__ import annotations

import statistics
from datetime import datetime
from pathlib import Path

from .metrics import family_label, format_snr_range
from .models import (
    AnalysisResult,
    LoadedData,
    LeaderboardRow,
    Zone,
)


def _fmt_gain(value: float) -> str:
    if value == float("inf"):
        return "inf"
    return f"{value:.2f}x"


def _fmt_experiments(experiments: tuple[str, ...]) -> str:
    """Сокращает список экспериментов для вывода.

    MC-эксперименты помечаются префиксом ``mc:``.
    """
    if not experiments:
        return ""
    if len(experiments) == 1:
        return f"[{experiments[0]}]"
    bulk = [e for e in experiments if not e.startswith("mc:")]
    mc = [e for e in experiments if e.startswith("mc:")]
    parts: list[str] = []
    if bulk:
        parts.append(f"{len(bulk)} bulk")
    if mc:
        parts.append(f"{len(mc)} MC")
    return f"[{', '.join(parts)}]"


def _zone_line(zone: Zone) -> str:
    experiment_str = _fmt_experiments(zone.experiments)
    t_mark = ""
    if zone.equal_t is False:
        t_mark = "  ⚠️ разный t"
    elif zone.equal_t is True:
        t_mark = "  ✓ равный t"
    return (
        f"- {zone.channel} | {zone.code_size} | {zone.decoder} | "
        f"SNR {format_snr_range((zone.snr_start, zone.snr_end))} | "
        f"средний gain {_fmt_gain(zone.mean_gain)} "
        f"{experiment_str} "
        f"(против {', '.join(family_label(c) for c in zone.competitors)})"
        f"{t_mark}"
    )


def _summary_section(data: LoadedData, analysis: AnalysisResult) -> list[str]:
    total = analysis.total_points
    wins = analysis.win_points
    losses = analysis.loss_points_count
    ties = total - wins - losses
    share = (wins / total * 100.0) if total else 0.0
    tie_share = (ties / total * 100.0) if total else 0.0
    loss_share = (losses / total * 100.0) if total else 0.0
    finite_gains = [p.gain for p in analysis.points if p.gain != float("inf")]
    mean_gain = sum(finite_gains) / len(finite_gains) if finite_gains else 0.0
    median_gain = statistics.median(finite_gains) if finite_gains else 0.0

    # Список уникальных экспериментов (bulk).
    bulk_experiments = sorted({r.experiment_name for r in data.bulk_results})
    mc_experiments = sorted({r.experiment_name for r in data.mc_results})

    lines = [
        "## Сводка",
        "",
        f"- **Источник данных**: bulk-файлов: {len(data.bulk_files)}; "
        f"Monte Carlo файлов: {len(data.mc_files)}",
        f"- **Эксперименты (bulk)**: {', '.join(bulk_experiments) if bulk_experiments else 'N/A'}",
        f"- **Эксперименты (MC)**: {', '.join(mc_experiments) if mc_experiments else 'N/A'}",
        f"- **Всего точек сравнения**: {total}",
        f"- **Значимых побед Wavelet**: {wins} ({share:.1f}%)",
        f"- **Ничьих (различие незначимо)**: {ties} ({tie_share:.1f}%)",
        f"- **Значимых поражений**: {losses} ({loss_share:.1f}%)",
        f"- **Средний gain (конечный)**: {_fmt_gain(mean_gain)}",
        f"- **Медиана gain**: {_fmt_gain(median_gain)}",
        f"- **Зон доминирования**: {len(analysis.zones)}",
        "",
        "> Победой считается только **статистически значимое** превосходство "
        "(z-score >= 2 по bulk-данным, непересечение 95% CI по MC) **и** "
        "относительный выигрыш BER не менее 2%. Различия ниже порога "
        "заносятся в ничьи.",
        "",
    ]
    if wins:
        known_eq = sum(1 for p in analysis.points if p.win and p.equal_capacity is True)
        known_neq = sum(1 for p in analysis.points if p.win and p.equal_capacity is False)
        if known_neq and known_neq > 0:
            lines.append(
                f"> ⚠️ **Важно про честность:** из {wins} значимых побед "
                f"**{known_neq}** получены при **разной ёмкости декодера** "
                f"(у Wavelet syndrome t выше, чем у конкурента — например "
                f"t=5 против t=4). Такие победы — следствие большего "
                f"расстояния d_min (оно и позволяет поставить t больше), "
                f"а не «волшебства» конструкции. Настоящее сравнение кодов "
                f"— только **{known_eq}** побед при **равном t**."
            )
            lines.append("")
    if data.warnings:
        lines.append("> ⚠️ Предупреждения о данных:")
        lines.append("")
        for warning in data.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    return lines


def _best_zones_section(analysis: AnalysisResult) -> list[str]:
    lines = ["# 1. Лучшие области преимущества Wavelet", ""]
    if not analysis.zones:
        lines.append(
            "Нет точек, где Wavelet выигрывает у всех конкурентов одновременно."
        )
        lines.append("")
        return lines

    by_channel: dict[str, list[Zone]] = {}
    for zone in analysis.zones:
        by_channel.setdefault(zone.channel, []).append(zone)

    for channel in sorted(by_channel):
        lines.append(f"## Канал: {channel}")
        lines.append("")
        zones = sorted(by_channel[channel], key=lambda z: z.mean_gain, reverse=True)
        for zone in zones:
            lines.append(_zone_line(zone))
        lines.append("")
    return lines


def _vs_family_section(analysis: AnalysisResult) -> list[str]:
    lines = ["# 2. Сравнение Wavelet против каждого семейства кодов", ""]
    if not analysis.family_summaries:
        lines.append("Нет данных для попарного сравнения.")
        lines.append("")
        return lines

    for group in sorted(analysis.family_summaries):
        summary = analysis.family_summaries[group]
        label = family_label(group)
        ties = summary.comparisons - summary.wins - summary.losses
        win_rate = (summary.wins / summary.comparisons * 100.0) if summary.comparisons else 0.0
        lines.append(f"## Wavelet против {label}")
        lines.append("")
        lines.append(
            f"Побед: **{summary.wins}** | "
            f"Ничьих: {ties} | "
            f"Поражений: {summary.losses} | "
            f"всего {summary.comparisons} "
            f"({win_rate:.1f}% побед) | "
            f"Средний gain: {_fmt_gain(summary.mean_gain)} | "
            f"Медиана: {_fmt_gain(summary.median_gain)}"
        )
        lines.append("")
        if summary.wins:
            breakdown = (
                f"    из побед **при равном t декодера**: {summary.wins_equal_t}; "
                f"при разном t (артефакт ёмкости): {summary.wins_unequal_t}; "
                f"t неизвестен (MC-без-config): {summary.wins_unknown_t}"
            )
            lines.append(breakdown)
            lines.append("")

        win_points = [p for p in summary.points if p.win]
        if not win_points:
            lines.append(f"Нет значимых побед Wavelet над {label}.")
            lines.append("")
            continue

        # Зоны побед по (канал, размер, декодер).
        zones = _local_zones(win_points)
        lines.append("> Топ-20 зон значимого преимущества:")
        lines.append("")
        for zone in zones[:20]:
            lines.append(_zone_line(zone))
        lines.append("")
    return lines


def _local_zones(points) -> list[Zone]:
    from .analyzer import _zones_from_points

    return sorted(
        _zones_from_points(points, require_win=True),
        key=lambda z: z.mean_gain,
        reverse=True,
    )


def _mc_section(analysis: AnalysisResult, data: LoadedData) -> list[str]:
    lines = ["# 4. Подтверждение Monte Carlo", ""]
    if not data.mc_files:
        lines.append(
            "MC-данные не найдены (ожидались results/mc_*/"
            "wavelet_channel_decoder_statistics*.csv). Раздел пропущен."
        )
        lines.append("")
        return lines

    lines.append(f"Подтверждённых MC-зон (совпали с bulk): **{len(analysis.mc_confirmed)}**")
    lines.append("")
    for zone in analysis.mc_confirmed:
        lines.append(_zone_line(zone))
    lines.append("")

    lines.append(
        f"Неподтверждённых/нестабильных MC-зон: **{len(analysis.mc_unstable)}**"
    )
    lines.append("")
    for zone in analysis.mc_unstable:
        lines.append(_zone_line(zone))
    lines.append("")
    return lines


def _loss_section(analysis: AnalysisResult) -> list[str]:
    lines = ["# 5. Области, где Wavelet уступает конкурентам", ""]
    # Значимые поражения (loss=True): значимо И выше порога содержательности.
    loss_points = analysis.loss_points
    if not loss_points:
        lines.append("Значимых областей проигрыша не обнаружено.")
        lines.append("")
        return lines

    lines.append(
        f"Точек со **значимым** превосходством конкурента: **{len(loss_points)}**"
    )
    lines.append("")

    grouped: dict[tuple[str, str, str], list] = {}
    for p in loss_points:
        grouped.setdefault((p.channel, p.code_size, p.decoder), []).append(p)

    for (channel, size, decoder), points in sorted(grouped.items()):
        competitors = sorted({p.competitor for p in points})
        snrs = sorted({p.snr for p in points})
        lines.append(
            f"- {channel} | {size} | {decoder} | SNR "
            f"{_collapse(snrs)} | уступает: "
            f"{', '.join(family_label(c) for c in competitors)}"
        )
    lines.append("")
    return lines


def _collapse(snrs: list[float]) -> str:
    from .metrics import snr_intervals

    intervals = snr_intervals(snrs)
    return "; ".join(format_snr_range(i) for i in intervals)


def _capacity_verdict_section(analysis: AnalysisResult) -> list[str]:
    """CI-вердикты по точкам с равным syndrome_t: кто настоящий код лучше.

    Победой/поражением считается только непересечение 95% CI двух
    независимых MC-выборок (50 сидов). Это самый честный срез: один и тот
    же t/p у обеих сторон, различие видно по доверительным интервалам.
    """
    verdicts = analysis.capacity_verdicts
    if not verdicts:
        return [
            "# 3. Равная ёмкость декодера (CI по сидам)",
            "",
            "Нет точек, где сравниваемые коды имели бы одинаковый "
            "syndrome t **и** MC-CI по обоим. Раздел пропущен.",
            "",
        ]

    lines = [
        "# 3. Равная ёмкость декодера (CI по сидам)",
        "",
        "> Самый честный срез: Wavelet vs конкурент **при равном syndrome "
        "t**, вердикт по непересечению 95% CI 50 независимых сидов. "
        "Разный t (артефакт ёмкости) сюда не входит.",
        "",
    ]
    for v in verdicts:
        if v.wavelet_wins > v.competitor_wins:
            call = f"**Wavelet** лучше в {v.wavelet_wins}/{v.total}"
        elif v.competitor_wins > v.wavelet_wins:
            call = (
                f"**{family_label(v.competitor)}** лучше в "
                f"{v.competitor_wins}/{v.total}"
            )
        else:
            call = "паритет"
        lines.append(
            f"- {v.channel} | {v.code_size} | {v.decoder} | "
            f"против {family_label(v.competitor)}: "
            f"win={v.wavelet_wins} tie={v.ties} loss={v.competitor_wins} "
            f"/ {v.total} → {call}"
        )
    lines.append("")
    return lines


def _leaderboard_section(analysis: AnalysisResult) -> list[str]:
    lines = ["# 6. Таблица лидеров", ""]
    if not analysis.leaderboard:
        lines.append("Таблица пуста: нет зон доминирования.")
        lines.append("")
        return lines

    lines.append("| Channel | Code size | Decoder | SNR range | Gain | t-честность | Experiment |")
    lines.append("|---------|-----------|---------|-----------|------|-------------|------------|")
    for row in analysis.leaderboard:
        experiment_str = _fmt_experiments(row.experiments)
        lines.append(
            f"| {row.channel} | {row.code_size} | {row.decoder} | "
            f"{row.snr_range} | {_fmt_gain(row.mean_gain)} | "
            f"{row.equal_t_label} | {experiment_str} |"
        )
    lines.append("")
    return lines


def build_report(data: LoadedData, analysis: AnalysisResult) -> str:
    """Собирает Markdown-отчёт целиком."""
    lines: list[str] = [
        "# Wavelet Code Advantage Report",
        "",
        f"Сформирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "> Сравнение производительности **Wavelet** кодов против конкурентов "
        "(BCH, Goppa, LDPC, Reed-Solomon) на различных каналах связи.",
        "",
    ]
    lines.extend(_summary_section(data, analysis))
    lines.extend(["---", ""])
    lines.extend(_best_zones_section(analysis))
    lines.extend(["---", ""])
    lines.extend(_vs_family_section(analysis))
    lines.extend(["---", ""])
    lines.extend(_capacity_verdict_section(analysis))
    lines.extend(["---", ""])
    lines.extend(_mc_section(analysis, data))
    lines.extend(["---", ""])
    lines.extend(_loss_section(analysis))
    lines.extend(["---", ""])
    lines.extend(_leaderboard_section(analysis))
    lines.extend(["---", ""])
    lines.extend(["# 7. Итоговые выводы", ""])
    if analysis.conclusions:
        for conclusion in analysis.conclusions:
            lines.append(f"- {conclusion}")
    else:
        lines.append("Выводы не сформированы: недостаточно данных.")
    lines.append("")
    return "\n".join(lines)


def write_report(
    data: LoadedData,
    analysis: AnalysisResult,
    output_path: Path,
) -> str:
    """Пишет отчёт в файл и возвращает его содержимое."""
    content = build_report(data, analysis)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content
