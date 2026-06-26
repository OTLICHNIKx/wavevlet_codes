from dataclasses import replace

from research.config import DEFAULT_RESEARCH_CONFIG
from research.runner import run_research


def main() -> None:
    """
    Маленький тестовый запуск исследования.

    Проверяем:
        message_count = 100
        Eb/N0 = 1.0 dB
        коды: (16,8), (32,16), (64,32)

    Результат сохраняется в:
        research_results/small_test/summary.csv
    """
    config = replace(
        DEFAULT_RESEARCH_CONFIG,
        message_count=100,
        ebn0_db_values=(1.0,),
        results_dir="research_results/small_test",
    )

    run_research(config)


if __name__ == "__main__":
    main()