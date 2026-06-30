from dataclasses import replace

from research.config import DEFAULT_RESEARCH_CONFIG
from research.runner import run_research


def main() -> None:
    config = replace(
        DEFAULT_RESEARCH_CONFIG,
        message_count=100,
        ebn0_db_values=(1.0,),
        results_dir="research_results/test_64_32_t5",
    )

    run_research(config)


if __name__ == "__main__":
    main()