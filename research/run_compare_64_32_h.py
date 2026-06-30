from dataclasses import replace
from typing import Iterable

from research.config import DEFAULT_RESEARCH_CONFIG, CodeResearchConfig
from research.runner import build_code_from_config, run_research, write_summary_csv


MESSAGE_COUNT = 20_000

EBN0_DB_VALUES = (
        0.0,
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
)

RESULTS_ROOT = "research_results/compare_64_32_h"

# Чтобы большой прогон не был слишком долгим.
# Главное: для baseline и BCH-like значение должно быть одинаковым.
CHASE_P_64_32 = 8

# True — сравниваем только код (64,32).
# Это быстрее и логичнее, потому что h меняется только у него.
# False — прогоняем все три кода в обоих экспериментах.
COMPARE_ONLY_64_32 = False


BCH_LIKE_H_64_32 = (
    1, 0, 1, 1, 1, 1,
    1, 0, 0, 1, 1, 1,
    1, 0, 1, 1, 0, 0,
    1, 0, 1, 1, 0, 0,
    1, 1, 1, 1, 0, 0,
    1, 1
)


def get_baseline_h_64_32() -> tuple[int, ...]:
    """
    Берёт старый h для (64,32) из DEFAULT_RESEARCH_CONFIG.
    """
    for code_config in DEFAULT_RESEARCH_CONFIG.codes:
        if code_config.name == "wavelet_64_32":
            return code_config.h

    raise ValueError("В DEFAULT_RESEARCH_CONFIG не найден код wavelet_64_32")


def make_code_configs_for_experiment(
    h_64_32: tuple[int, ...],
) -> tuple[CodeResearchConfig, ...]:
    """
    Создаёт список кодов для одного эксперимента.

    Меняем только h у wavelet_64_32.
    Остальные коды либо оставляем, либо исключаем,
    если COMPARE_ONLY_64_32 = True.
    """
    code_configs: list[CodeResearchConfig] = []

    for code_config in DEFAULT_RESEARCH_CONFIG.codes:
        if COMPARE_ONLY_64_32 and code_config.name != "wavelet_64_32":
            continue

        if code_config.name == "wavelet_64_32":
            code_config = replace(
                code_config,
                h=h_64_32,
                chase_unreliable_positions_count=CHASE_P_64_32,
            )

        code_configs.append(code_config)

    return tuple(code_configs)


def validate_h(
    experiment_name: str,
    h_64_32: tuple[int, ...],
) -> None:
    """
    Быстрая проверка: строится ли код с заданным h.
    """
    print()
    print("-" * 70)
    print(f"Проверка h для эксперимента: {experiment_name}")
    print("h length =", len(h_64_32))
    print("h weight =", sum(h_64_32))

    code_config = next(
        item
        for item in DEFAULT_RESEARCH_CONFIG.codes
        if item.name == "wavelet_64_32"
    )

    test_code_config = replace(
        code_config,
        h=h_64_32,
        chase_unreliable_positions_count=CHASE_P_64_32,
    )

    code = build_code_from_config(test_code_config)

    print("Код успешно построен")
    print("n =", code.n)
    print("k =", code.k)
    print("-" * 70)


def run_h_experiment(
    experiment_name: str,
    h_64_32: tuple[int, ...],
) -> list[dict]:
    """
    Запускает один эксперимент:
        baseline или bch_like.
    """
    validate_h(
        experiment_name=experiment_name,
        h_64_32=h_64_32,
    )

    code_configs = make_code_configs_for_experiment(
        h_64_32=h_64_32,
    )

    config = replace(
        DEFAULT_RESEARCH_CONFIG,
        message_count=MESSAGE_COUNT,
        ebn0_db_values=EBN0_DB_VALUES,
        codes=code_configs,
        results_dir=f"{RESULTS_ROOT}/{experiment_name}",
    )

    print()
    print("=" * 70)
    print(f"Запуск эксперимента: {experiment_name}")
    print("=" * 70)

    rows = run_research(config)

    for row in rows:
        row["experiment"] = experiment_name
        row["h_64_32_length"] = len(h_64_32)
        row["h_64_32_weight"] = sum(h_64_32)
        row["h_64_32"] = " ".join(str(value) for value in h_64_32)

    return rows


def main() -> None:
    baseline_h = get_baseline_h_64_32()

    all_rows: list[dict] = []
    baseline_rows = run_h_experiment(
        experiment_name="baseline",
        h_64_32=baseline_h,
    )
    all_rows.extend(baseline_rows)

    bch_like_rows = run_h_experiment(
        experiment_name="bch_like",
        h_64_32=BCH_LIKE_H_64_32,
    )
    all_rows.extend(bch_like_rows)

    combined_output_path = f"{RESULTS_ROOT}/summary.csv"

    write_summary_csv(
        rows=all_rows,
        output_path=combined_output_path,
    )

    print()
    print("=" * 70)
    print("Сравнение завершено.")
    print("Общий файл:", combined_output_path)
    print("Baseline:", f"{RESULTS_ROOT}/baseline/summary.csv")
    print("BCH-like:", f"{RESULTS_ROOT}/bch_like/summary.csv")
    print("=" * 70)


if __name__ == "__main__":
    main()