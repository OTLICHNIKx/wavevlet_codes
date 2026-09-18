from dataclasses import replace

from research.config import DEFAULT_RESEARCH_CONFIG
from research.runner import run_research


def main() -> None:
    """
    Основной прогон исследования.

    Параметры:
        message_count = 10_000
        Eb/N0 = 0.0 ... 3.5 dB
        коды: (16,8), (32,16), (64,32)

    Результат:
        research_results/full_10000/summary.csv
    """
    base_config = DEFAULT_RESEARCH_CONFIG

    # Для большого прогона оставляем p=8 для (64,32),
    # иначе Chase может выполняться очень долго.
    tuned_codes = tuple(
        replace(code_config, chase_unreliable_positions_count=8)
        if code_config.name == "wavelet_64_32"
        else code_config
        for code_config in base_config.codes
    )

    config = replace(
        base_config,
        message_count=10_000,
        ebn0_db_values=(
            0.0,
            0.5,
            1.0,
            1.5,
            2.0,
            2.5,
            3.0,
            3.5,
        ),
        codes=tuned_codes,
        results_dir="research_results/full_10000",
    )

    run_research(config)


if __name__ == "__main__":
    main()