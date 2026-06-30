import csv
import os
import zipfile
from collections import defaultdict

import matplotlib.pyplot as plt

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def find_project_file(relative_path: str) -> Path:
    """
    Ищет файл вверх по папкам от текущего скрипта.
    """
    for directory in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        candidate = directory / relative_path

        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Не найден файл {relative_path}. "
        f"Проверь, где лежит summary.csv."
    )

INPUT_CSV = find_project_file(
    "research_results/compare_64_32_h/summary.csv"
)

PROJECT_ROOT = INPUT_CSV.parents[2]
OUTPUT_DIR = PROJECT_ROOT / "research_results" / "plots"


def read_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("skipped", "").strip().lower() == "true":
                continue

            try:
                row["ebn0_db_float"] = float(row["ebn0_db"])
            except (KeyError, ValueError):
                continue

            for metric in ("ber", "frame_error_rate"):
                value = row.get(metric, "")
                if value == "":
                    row[metric + "_float"] = None
                else:
                    try:
                        row[metric + "_float"] = float(value)
                    except ValueError:
                        row[metric + "_float"] = None

            rows.append(row)

    return rows


def safe_filename(text):
    result = []
    for ch in text:
        if ch.isalnum() or ch in ("_", "-", "."):
            result.append(ch)
        else:
            result.append("_")
    return "".join(result)


def plot_metric_for_code(rows, experiment, code_name, metric_key, metric_label, output_name):
    selected = [
        row for row in rows
        if row.get("experiment") == experiment and row.get("code_name") == code_name
    ]

    by_decoder = defaultdict(list)

    for row in selected:
        value = row.get(metric_key + "_float")
        if value is None or value <= 0:
            continue
        by_decoder[row["decoder"]].append((row["ebn0_db_float"], value))

    if not by_decoder:
        return None

    plt.figure(figsize=(8, 5))

    decoder_order = ("syndrome", "hard_mld", "soft_mld", "chase")

    for decoder in decoder_order:
        if decoder not in by_decoder:
            continue

        points = sorted(by_decoder[decoder], key=lambda item: item[0])
        x_values = [item[0] for item in points]
        y_values = [item[1] for item in points]

        if decoder == "chase":
            plt.semilogy(
                x_values,
                y_values,
                marker="s",
                linewidth=3.0,
                linestyle="--",
                label=decoder,
                zorder=20,
            )
        else:
            plt.semilogy(
                x_values,
                y_values,
                marker="o",
                linewidth=1.8,
                label=decoder,
                zorder=10,
            )

    plt.xlabel("Eb/N0, dB")
    plt.ylabel(metric_label)
    plt.title(f"{metric_label} от Eb/N0 для {code_name} ({experiment})")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()

    output_path = os.path.join(OUTPUT_DIR, output_name)
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def plot_64_32_compare(rows, metric_key, metric_label, output_name):
    selected = [
        row for row in rows
        if row.get("code_name") == "wavelet_64_32"
        and row.get("decoder") == "chase"
        and row.get("experiment") in ("baseline", "bch_like")
    ]

    by_experiment = defaultdict(list)

    for row in selected:
        value = row.get(metric_key + "_float")
        if value is None or value <= 0:
            continue
        by_experiment[row["experiment"]].append((row["ebn0_db_float"], value))

    if not by_experiment:
        return None

    plt.figure(figsize=(8, 5))

    for experiment, points in sorted(by_experiment.items()):
        points = sorted(points, key=lambda item: item[0])
        x_values = [item[0] for item in points]
        y_values = [item[1] for item in points]
        plt.semilogy(x_values, y_values, marker="o", linewidth=1.8, label=experiment)

    plt.xlabel("Eb/N0, dB")
    plt.ylabel(metric_label)
    plt.title(f"{metric_label} от Eb/N0 для wavelet_64_32, Chase")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()

    output_path = os.path.join(OUTPUT_DIR, output_name)
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("INPUT_CSV =", INPUT_CSV)
    print("OUTPUT_DIR =", OUTPUT_DIR)

    rows = read_rows(INPUT_CSV)

    created = []

    code_names = (
        "wavelet_16_8",
        "wavelet_32_16",
        "wavelet_64_32",
    )

    experiments = (
        "baseline",
        "bch_like",
    )

    for experiment in experiments:
        for code_name in code_names:
            created.append(
                plot_metric_for_code(
                    rows=rows,
                    experiment=experiment,
                    code_name=code_name,
                    metric_key="ber",
                    metric_label="BER",
                    output_name=f"{safe_filename(code_name)}_{experiment}_BER_log.png",
                )
            )

            created.append(
                plot_metric_for_code(
                    rows=rows,
                    experiment=experiment,
                    code_name=code_name,
                    metric_key="frame_error_rate",
                    metric_label="FER",
                    output_name=f"{safe_filename(code_name)}_{experiment}_FER_log.png",
                )
            )

    created.append(
        plot_64_32_compare(
            rows=rows,
            metric_key="ber",
            metric_label="BER",
            output_name="wavelet_64_32_chase_baseline_vs_bch_like_BER_log.png",
        )
    )

    created.append(
        plot_64_32_compare(
            rows=rows,
            metric_key="frame_error_rate",
            metric_label="FER",
            output_name="wavelet_64_32_chase_baseline_vs_bch_like_FER_log.png",
        )
    )

    created = [path for path in created if path is not None]

    print("Создано графиков:", len(created))

    for path in created:
        print(path)


if __name__ == "__main__":
    main()
