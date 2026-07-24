import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def string_to_bool(value: str) -> bool:
    """
    Преобразует строковое значение из CSV в bool.
    """
    return value.strip().lower() in {
        "true",
        "1",
        "yes",
    }


def load_summary(
    summary_path: Path,
) -> list[dict[str, Any]]:
    """
    Загружает результаты исследования из summary.csv.

    Пропущенные декодеры и строки без метрик
    не включаются в графики.
    """
    if not summary_path.exists():
        raise FileNotFoundError(
            f"Файл результатов не найден: {summary_path}"
        )

    rows: list[dict[str, Any]] = []

    with summary_path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for source_row in reader:
            if string_to_bool(
                source_row.get("skipped", "false")
            ):
                continue

            if not source_row.get("ber", "").strip():
                continue

            row: dict[str, Any] = dict(source_row)

            row["ebn0_db"] = float(
                source_row["ebn0_db"]
            )

            row["ber"] = float(
                source_row["ber"]
            )

            row["frame_error_rate"] = float(
                source_row["frame_error_rate"]
            )

            row["failure_rate"] = float(
                source_row["failure_rate"]
            )

            row["avg_time_ms"] = float(
                source_row["avg_time_ms"]
            )

            row["message_count"] = int(
                source_row["message_count"]
            )

            row["total_bits"] = int(
                source_row["total_bits"]
            )

            rows.append(row)

    if not rows:
        raise ValueError(
            "В summary.csv отсутствуют строки с метриками"
        )

    return rows


def build_series(
    rows: list[dict[str, Any]],
) -> dict[
    tuple[str, str],
    list[dict[str, Any]],
]:
    """
    Группирует результаты по паре:

        код + декодер
    """
    grouped: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in rows:
        key = (
            str(row["code_name"]),
            str(row["decoder"]),
        )

        grouped[key].append(row)

    for series_rows in grouped.values():
        series_rows.sort(
            key=lambda item: item["ebn0_db"]
        )

    return dict(grouped)


def logarithmic_display_value(
    row: dict[str, Any],
    metric: str,
) -> float:
    """
    На логарифмической шкале нельзя показать ноль.

    Если в эксперименте получен ноль ошибок,
    отображаем половину минимальной измеримой частоты.

    Это только способ отображения.
    Исходное значение в CSV остаётся равным нулю.
    """
    value = float(row[metric])

    if value > 0:
        return value

    if metric == "ber":
        denominator = int(row["total_bits"])
    else:
        denominator = int(row["message_count"])

    return 0.5 / denominator


def plot_error_metric(
    grouped: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ],
    metric: str,
    title: str,
    y_label: str,
    output_path: Path,
) -> None:
    """
    Строит график ошибки в логарифмическом масштабе.
    """
    figure, axis = plt.subplots(
        figsize=(10, 6)
    )

    for (
        code_name,
        decoder_name,
    ), series_rows in sorted(grouped.items()):
        x_values = [
            row["ebn0_db"]
            for row in series_rows
        ]

        y_values = [
            logarithmic_display_value(
                row=row,
                metric=metric,
            )
            for row in series_rows
        ]

        axis.semilogy(
            x_values,
            y_values,
            marker="o",
            label=(
                f"{code_name} / "
                f"{decoder_name}"
            ),
        )

    axis.set_title(title)
    axis.set_xlabel("Eb/N0, dB")
    axis.set_ylabel(y_label)

    axis.grid(
        True,
        which="both",
        alpha=0.35,
    )

    axis.legend()
    figure.tight_layout()

    figure.savefig(
        output_path,
        dpi=200,
    )

    plt.close(figure)


def plot_time_metric(
    grouped: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ],
    output_path: Path,
) -> None:
    """
    Строит график среднего времени декодирования.
    """
    figure, axis = plt.subplots(
        figsize=(10, 6)
    )

    for (
        code_name,
        decoder_name,
    ), series_rows in sorted(grouped.items()):
        x_values = [
            row["ebn0_db"]
            for row in series_rows
        ]

        y_values = [
            row["avg_time_ms"]
            for row in series_rows
        ]

        axis.plot(
            x_values,
            y_values,
            marker="o",
            label=(
                f"{code_name} / "
                f"{decoder_name}"
            ),
        )

    axis.set_title(
        "Среднее время декодирования"
    )

    axis.set_xlabel("Eb/N0, dB")
    axis.set_ylabel(
        "Среднее время на сообщение, ms"
    )

    axis.grid(
        True,
        alpha=0.35,
    )

    axis.legend()
    figure.tight_layout()

    figure.savefig(
        output_path,
        dpi=200,
    )

    plt.close(figure)


def build_plots(
    summary_path: Path,
) -> list[Path]:
    """
    Строит основные графики исследования.
    """
    rows = load_summary(summary_path)
    grouped = build_series(rows)

    output_directory = (
        summary_path.parent / "plots"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_paths = {
        "ber": output_directory / "ber.png",
        "fer": output_directory / "fer.png",
        "failure": (
            output_directory / "failure_rate.png"
        ),
        "time": (
            output_directory / "decoding_time.png"
        ),
    }

    plot_error_metric(
        grouped=grouped,
        metric="ber",
        title=(
            "BER для Wavelet- и BCH-кодов"
        ),
        y_label="BER",
        output_path=output_paths["ber"],
    )

    plot_error_metric(
        grouped=grouped,
        metric="frame_error_rate",
        title=(
            "FER для Wavelet- и BCH-кодов"
        ),
        y_label="FER",
        output_path=output_paths["fer"],
    )

    plot_error_metric(
        grouped=grouped,
        metric="failure_rate",
        title=(
            "Доля неуспешных декодирований"
        ),
        y_label="Failure rate",
        output_path=output_paths["failure"],
    )

    plot_time_metric(
        grouped=grouped,
        output_path=output_paths["time"],
    )

    return list(output_paths.values())


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Построение графиков по summary.csv"
        )
    )

    parser.add_argument(
        "summary_path",
        nargs="?",
        default=(
            "research_results/"
            "preliminary_wavelet_bch/"
            "summary.csv"
        ),
        help="Путь к summary.csv",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    output_paths = build_plots(
        Path(arguments.summary_path)
    )

    print("Графики сохранены:")

    for output_path in output_paths:
        print(f"  {output_path}")


if __name__ == "__main__":
    main()