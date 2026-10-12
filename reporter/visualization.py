"""Генерация графиков отчёта (BER-кривые, heatmap, таблица лидеров)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .metrics import family_label  # noqa: E402
from .models import (  # noqa: E402
    AnalysisResult,
    ExperimentResult,
    FAMILY_LABELS,
    LoadedData,
)


_FAMILY_STYLE: dict[str, dict[str, str]] = {
    "wavelet": {"color": "#d62728", "marker": "o", "linestyle": "-"},
    "bch": {"color": "#1f77b4", "marker": "s", "linestyle": "--"},
    "goppa": {"color": "#2ca02c", "marker": "^", "linestyle": "-."},
    "reed_solomon": {"color": "#9467bd", "marker": "D", "linestyle": ":"},
    "ldpc": {"color": "#ff7f0e", "marker": "v", "linestyle": "--"},
}


def _style(group: str) -> dict[str, str]:
    return _FAMILY_STYLE.get(
        group, {"color": "gray", "marker": "x", "linestyle": "-"}
    )


def plot_ber_curves(
    data: LoadedData,
    output_dir: Path,
    *,
    source: str = "bulk",
) -> list[str]:
    """BER vs SNR по каждому (канал, размер, декодер)."""
    created: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    # (channel, size, decoder) -> family -> [(snr, ber)]
    series: dict[tuple[str, str, str], dict[str, dict[float, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for r in data.results:
        if r.source != source or r.ber is None or r.snr is None:
            continue
        if r.n is None or r.k is None:
            continue
        series[(r.channel, r.code_size, r.decoder)][r.family_group][r.snr].append(r.ber)

    for (channel, size, decoder), families in sorted(series.items()):
        if not families:
            continue
        fig, ax = plt.subplots(figsize=(9, 6))
        plotted = False
        for group, snr_map in sorted(families.items()):
            snrs = sorted(snr_map)
            bers = [min(snr_map[s]) for s in snrs]
            positive = [(s, b) for s, b in zip(snrs, bers) if b and b > 0]
            if not positive:
                continue
            xs, ys = zip(*positive)
            style = _style(group)
            ax.semilogy(
                xs,
                ys,
                label=family_label(group),
                color=style["color"],
                marker=style["marker"],
                linestyle=style["linestyle"],
                markersize=5,
            )
            plotted = True

        if not plotted:
            plt.close(fig)
            continue

        ax.set_xlabel("Eb/N0, dB")
        ax.set_ylabel("BER")
        ax.set_title(f"BER vs SNR — {channel}, {size}, {decoder}")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        fig.tight_layout()

        safe = f"{source}_ber_{channel}_{size}_{decoder}.png".replace("/", "-")
        path = output_dir / safe
        fig.savefig(path, dpi=120)
        plt.close(fig)
        created.append(str(path))

    return created


def plot_gain_heatmap(
    analysis: AnalysisResult,
    output_dir: Path,
) -> list[str]:
    """Heatmap log10(gain) по осям SNR x канал."""
    created: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    points = analysis.points
    if not points:
        return created

    channels = sorted({p.channel for p in points})
    snrs = sorted({p.snr for p in points})
    if not channels or not snrs:
        return created

    # Средний gain по (channel, snr) среди конечных значений.
    buckets: dict[tuple[str, float], list[float]] = defaultdict(list)
    for p in points:
        if p.gain != float("inf"):
            buckets[(p.channel, p.snr)].append(p.gain)

    matrix = np.full((len(channels), len(snrs)), np.nan)
    for i, channel in enumerate(channels):
        for j, snr in enumerate(snrs):
            gains = buckets.get((channel, snr))
            if gains:
                matrix[i, j] = np.log10(max(np.mean(gains), 1e-12))

    fig, ax = plt.subplots(figsize=(max(8, len(snrs) * 0.9), max(3, len(channels) * 1.1)))
    masked = np.ma.masked_invalid(matrix)
    image = ax.imshow(masked, aspect="auto", cmap="RdYlGn")
    ax.set_xticks(range(len(snrs)))
    ax.set_xticklabels([f"{s:g}" for s in snrs])
    ax.set_yticks(range(len(channels)))
    ax.set_yticklabels(channels)
    ax.set_xlabel("SNR, dB")
    ax.set_ylabel("Канал")
    ax.set_title("Преимущество Wavelet: log10(gain), gain>0 — красный/жёлтый")
    fig.colorbar(image, ax=ax, label="log10(BER_other / BER_wavelet)")
    fig.tight_layout()

    path = output_dir / "gain_heatmap.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    created.append(str(path))
    return created


def plot_leaderboard(
    analysis: AnalysisResult,
    output_dir: Path,
) -> list[str]:
    """Горизонтальная диаграмма топ-зон по среднему выигрышу."""
    created: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = analysis.leaderboard[:15]
    if not rows:
        return created

    labels = [
        f"{r.channel} {r.code_size}\n{r.decoder} {r.snr_range}" for r in rows
    ]
    values = [r.mean_gain for r in rows]

    fig, ax = plt.subplots(figsize=(10, max(3, 0.5 * len(rows) + 2)))
    positions = range(len(rows))
    ax.barh(list(positions), values, color="#d62728", alpha=0.8)
    ax.set_yticks(list(positions))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Средний gain (BER_other / BER_wavelet)")
    ax.set_title("Зоны доминирования Wavelet (топ по среднему выигрышу)")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()

    path = output_dir / "leaderboard.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    created.append(str(path))
    return created


def generate_all(
    data: LoadedData,
    analysis: AnalysisResult,
    output_dir: Path,
) -> list[str]:
    """Все графики отчёта."""
    created: list[str] = []
    created.extend(plot_ber_curves(data, output_dir / "ber_curves", source="bulk"))
    created.extend(plot_ber_curves(data, output_dir / "ber_curves", source="monte_carlo"))
    created.extend(plot_gain_heatmap(analysis, output_dir))
    created.extend(plot_leaderboard(analysis, output_dir))
    return created
