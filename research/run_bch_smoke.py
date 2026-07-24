from research.config import (
    BCH_SMOKE_RESEARCH_CONFIG,
)

from research.runner import run_research


def main() -> None:
    """
    Первый интеграционный запуск Wavelet и BCH-кодов
    через общий исследовательский pipeline.
    """
    run_research(
        BCH_SMOKE_RESEARCH_CONFIG
    )


if __name__ == "__main__":
    main()