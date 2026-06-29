from dataclasses import replace

from research.config import DEFAULT_RESEARCH_CONFIG
from research.dataset import build_dataset_for_code
from research.runner import run_code_research, write_summary_csv


def main() -> None:
    """
    Маленький эксперимент для подбора p в алгоритме Чейза.

    Исследуем только код (64,32):
        message_count = 100
        Eb/N0 = 3.5 dB
        t = 2
        p = 8, 10, 12

    Цель:
        понять, уменьшается ли FER / failure_rate при увеличении p.
    """
    base_config = DEFAULT_RESEARCH_CONFIG

    code_64_32 = next(
        code_config
        for code_config in base_config.codes
        if code_config.name == "wavelet_64_32"
    )

    p_values = (8, 10, 12)

    all_rows = []

    for p in p_values:
        print()
        print("=" * 70)
        print(f"Тест Chase для (64,32): p = {p}, t = 2")
        print("=" * 70)

        code_config = replace(
            code_64_32,
            chase_unreliable_positions_count=p,
        )

        decoder_config = replace(
            base_config.decoders,
            run_syndrome=False,
            run_hard_mld=False,
            run_soft_mld=False,
            run_chase=True,
            syndrome_max_error_weight=2,
            chase_inner_decoder_max_error_weight=2,
        )

        dataset = build_dataset_for_code(
            message_count=100,
            code_config=code_config,
            message_seed=base_config.message_seed,
            noise_seed=base_config.noise_seed,
        )

        rows = run_code_research(
            code_config=code_config,
            dataset=dataset,
            decoder_config=decoder_config,
            ebn0_db_values=(3.5,),
        )

        for row in rows:
            row["chase_p"] = p
            row["syndrome_t"] = 2

        all_rows.extend(rows)

    output_path = "research_results/chase_p_sweep_64_32/summary.csv"

    write_summary_csv(
        rows=all_rows,
        output_path=output_path,
    )

    print()
    print("Подбор p завершён.")
    print("Файл результатов:", output_path)


if __name__ == "__main__":
    main()