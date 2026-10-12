"""Веб-интерфейс репортера: загрузка CSV -> анализ -> HTML-отчёт.

Запуск:

    python -m reporter.web
    # затем открыть http://127.0.0.1:5000

Загруженный CSV сохраняется во временный каталог, читается теми же
функциями ``reporter.loader``, что и CLI-репортер, поэтому результат
веба и командной строки совпадают.

Поддерживаются оба формата, которые понимает CLI:

1. ``summary.csv`` (широкая таблица runner'а) — колонки
   ``code_name, code_family, n, k, ebn0_db, decoder, ber, ...``.
   Нужно указать канал и имя эксперимента (форма не примет файл без них).
2. ``*_all_metrics.csv`` / ``wavelet_channel_decoder_statistics.csv``
   (Monte Carlo, long или wide) — канал берётся из колонки ``channel``.
"""

from __future__ import annotations

import argparse
import base64
import io
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from flask import (  # noqa: E402
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .analyzer import analyze  # noqa: E402
from .loader import load_bulk_summary, load_mc_statistics  # noqa: E402
from .metrics import family_label, format_snr_range  # noqa: E402
from .models import LoadedData  # noqa: E402

app = Flask(__name__)
app.secret_key = "wavelet-reporter-local"

# Лимит на размер загрузки: 16 МБ с запасом на большие summary.csv.
_MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Колонки-маркеры, по которым определяется формат файла.
_BULK_MARKER = "ebn0_db"
_MC_LONG_MARKER = "metric"
_MC_WIDE_MARKER = "mean_BER"


def _detect_format(header: list[str]) -> str:
    """Определяет формат CSV по именам колонок."""
    columns = {name.strip() for name in header}
    if _BULK_MARKER in columns and "ber" in columns:
        return "bulk"
    if _MC_LONG_MARKER in columns:
        return "mc"
    if _MC_WIDE_MARKER in columns or "mean_ber" in columns:
        return "mc"
    if "ber" in columns and "code_name" in columns:
        return "bulk"
    if "code" in columns and "parameter" in columns:
        return "mc"
    return "unknown"


def _read_header(raw: bytes) -> list[str]:
    """Читает первую строку CSV. Работает на копии байтов: TextIOWrapper
    при сборке мусора закрывает поток, из которого читал."""
    import csv

    reader = csv.reader(
        io.StringIO(raw.decode("utf-8-sig", errors="replace"))
    )
    try:
        return next(reader)
    except StopIteration:
        return []


def _figure_to_data_uri(fig: plt.Figure) -> str:
    """Сериализует matplotlib-фигуру в data: URI для <img src=...>."""
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=110,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _plot_gain_curves(analysis) -> str | None:
    """Средний выигрыш Wavelet против всех конкурентов по SNR."""
    points = [p for p in analysis.points if _finite(p.gain)]
    if not points:
        return None

    by_snr: dict[float, list[float]] = {}
    for point in points:
        by_snr.setdefault(point.snr, []).append(float(point.gain))
    if not by_snr:
        return None

    snrs = sorted(by_snr)
    means = [sum(by_snr[s]) / len(by_snr[s]) for s in snrs]

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(snrs, means, marker="o", color="#d62728", linewidth=1.8)
    ax.axhline(1.0, color="#888", linestyle="--", linewidth=1.0)
    ax.set_yscale("log")
    ax.set_xlabel("Eb/N0, dB")
    ax.set_ylabel("Средний выигрыш Wavelet (x)")
    ax.set_title("Во сколько раз BER Wavelet ниже конкурентов")
    ax.grid(alpha=0.3)
    return _figure_to_data_uri(fig)


def _plot_family_bars(analysis) -> str | None:
    """Средний выигрыш по каждому семейству-конкуренту."""
    summaries = [
        s for s in analysis.family_summaries.values()
        if s.comparisons > 0 and _finite(s.mean_gain)
    ]
    if not summaries:
        return None

    summaries.sort(key=lambda s: s.mean_gain)
    labels = [family_label(s.competitor) for s in summaries]
    values = [float(s.mean_gain) for s in summaries]
    wins = [s.wins for s in summaries]

    fig, ax = plt.subplots(figsize=(7.5, 0.5 * len(labels) + 1.6))
    positions = range(len(labels))
    colors = ["#2ca02c" if v > 1 else "#d62728" for v in values]
    ax.barh(list(positions), values, color=colors)
    ax.axvline(1.0, color="#888", linestyle="--", linewidth=1.0)
    ax.set_yticks(list(positions))
    ax.set_yticklabels(labels)
    ax.set_xscale("log")
    ax.set_xlabel("Средний выигрыш Wavelet (x)")
    ax.set_title("Wavelet против каждого семейства")
    ax.grid(axis="x", alpha=0.3)
    for pos, value, win, total in zip(positions, values, wins, [s.comparisons for s in summaries]):
        ax.text(value, pos, f"  {win}/{total}", va="center", fontsize=8)
    return _figure_to_data_uri(fig)


def _plot_ber_curves(results) -> list[dict]:
    """BER-кривые по каждому (канал, размерность, декодер)."""
    from collections import defaultdict

    series: dict[tuple, dict[str, dict[float, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for r in results:
        if r.ber is None or r.snr is None or r.n is None or r.k is None:
            continue
        series[(r.channel, r.code_size, r.decoder)][r.family_group][r.snr].append(r.ber)

    from .visualization import _style

    out: list[dict] = []
    for (channel, size, decoder), families in sorted(series.items()):
        if "wavelet" not in families:
            continue
        fig, ax = plt.subplots(figsize=(7.5, 4.4))
        for group, points_by_snr in sorted(families.items()):
            snrs = sorted(points_by_snr)
            bers = [
                sum(points_by_snr[s]) / len(points_by_snr[s]) for s in snrs
            ]
            style = _style(group)
            ax.semilogy(
                snrs,
                bers,
                color=style["color"],
                marker=style["marker"],
                linestyle=style["linestyle"],
                label=family_label(group),
                linewidth=1.5,
                markersize=4,
            )
        ax.set_xlabel("Eb/N0, dB")
        ax.set_ylabel("BER")
        ax.set_title(f"{channel} | n/k = {size} | декодер: {decoder}")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8)
        out.append({
            "title": f"{channel} | {size} | {decoder}",
            "image": _figure_to_data_uri(fig),
        })
    return out


def _finite(value) -> bool:
    try:
        return value is not None and value == value and abs(value) != float("inf")
    except TypeError:
        return False


def _summarize(analysis, data: LoadedData) -> dict:
    total = analysis.total_points
    wins = analysis.win_points
    finite = [p.gain for p in analysis.points if _finite(p.gain)]
    return {
        "source_files": len(data.bulk_files) + len(data.mc_files),
        "rows": len(data.results),
        "comparisons": total,
        "wins": wins,
        "win_pct": (100.0 * wins / total) if total else 0.0,
        "mean_gain": (sum(finite) / len(finite)) if finite else None,
        "max_gain": max(finite) if finite else None,
        "zones": len(analysis.zones),
        "loss_points": len(analysis.loss_points),
    }


def _zone_rows(analysis) -> list[dict]:
    return [
        {
            "channel": z.channel,
            "size": z.code_size,
            "decoder": z.decoder,
            "snr": format_snr_range((z.snr_start, z.snr_end)),
            "gain": z.mean_gain,
            "competitors": ", ".join(
                family_label(g) for g in z.competitors
            ),
        }
        for z in sorted(
            analysis.zones,
            key=lambda z: -(z.mean_gain if _finite(z.mean_gain) else 0.0),
        )
    ]


def _family_rows(analysis) -> list[dict]:
    rows = []
    for summary in analysis.family_summaries.values():
        rows.append({
            "family": family_label(summary.competitor),
            "wins": summary.wins,
            "comparisons": summary.comparisons,
            "win_pct": (
                100.0 * summary.wins / summary.comparisons
                if summary.comparisons else 0.0
            ),
            "mean_gain": summary.mean_gain,
            "max_gain": summary.max_gain,
            "snr_ranges": ", ".join(
                format_snr_range(iv) for iv in summary.snr_ranges
            ) or "—",
        })
    rows.sort(key=lambda r: -r["wins"])
    return rows


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        upload = request.files.get("csv_file")
        if upload is None or not upload.filename:
            flash("Файл не выбран", "error")
            return redirect(url_for("index"))

        raw = upload.read()
        fmt = _detect_format(_read_header(raw))
        if fmt == "unknown":
            flash(
                "Не удалось определить формат CSV. Ожидаются колонки "
                "ebn0_db+ber (summary) или metric+code (Monte Carlo).",
                "error",
            )
            return redirect(url_for("index"))

        suffix = Path(upload.filename).suffix or ".csv"
        # Загруженный файл живёт только до конца запроса: графики уже
        # встроены в HTML как base64, поэтому постоянного хранилища
        # не нужно и мусор не копится.
        handle = tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False
        )
        try:
            handle.write(raw)
            handle.close()

            channel = (request.form.get("channel") or "").strip()
            experiment = (request.form.get("experiment") or "").strip()
            if fmt == "bulk" and not channel:
                flash(
                    "Для summary.csv нужно указать канал "
                    "(например rayleigh или awgn).",
                    "error",
                )
                return redirect(url_for("index"))

            target = Path(handle.name)
            if fmt == "bulk":
                results = load_bulk_summary(
                    target,
                    channel=channel,
                    experiment_name=experiment or Path(upload.filename).stem,
                )
                files = [upload.filename]
            else:
                results = load_mc_statistics(target)
                files = [upload.filename]
        finally:
            Path(handle.name).unlink(missing_ok=True)

        if not results:
            flash(
                "В файле не нашлось подходящих строк (проверьте skipped и ber).",
                "error",
            )
            return redirect(url_for("index"))

        data = LoadedData(
            results=results,
            bulk_files=files if fmt == "bulk" else [],
            mc_files=files if fmt == "monte_carlo" else [],
            warnings=[],
        )
        analysis = analyze(data)

        return render_template(
            "report.html",
            summary=_summarize(analysis, data),
            zones=_zone_rows(analysis),
            families=_family_rows(analysis),
            conclusions=analysis.conclusions,
            loss_points=analysis.loss_points,
            gain_chart=_plot_gain_curves(analysis),
            family_chart=_plot_family_bars(analysis),
            ber_charts=_plot_ber_curves(results),
            warnings=data.warnings,
            filename=upload.filename,
        )

    return render_template("index.html")


def main() -> None:
    parser = argparse.ArgumentParser(description="Веб-интерфейс репортера")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app.config["MAX_CONTENT_LENGTH"] = _MAX_CONTENT_LENGTH

    print(f"Репортер: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
