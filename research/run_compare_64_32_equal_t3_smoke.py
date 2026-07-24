from research.config import (
    COMPARE_64_32_EQUAL_T3_SMOKE_CONFIG,
)

from research.runner import run_research


def main() -> None:
    """
    Предварительное сравнение кодов:

        Wavelet [64,32]
        BCH-derived [64,32]

    У обоих кодов одинаковые настройки:

        syndrome t=3
        Chase t=3, p=6
    """
    run_research(
        COMPARE_64_32_EQUAL_T3_SMOKE_CONFIG
    )


if __name__ == "__main__":
    main()