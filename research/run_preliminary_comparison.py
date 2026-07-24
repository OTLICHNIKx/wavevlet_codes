from research.config import (
    PRELIMINARY_WAVELET_BCH_CONFIG,
)

from research.runner import run_research


def main() -> None:
    """
    Предварительное сравнение:

        Wavelet(64,32)
        BCH(63,45)

    Используются одинаковые декодеры и их параметры.
    """
    run_research(
        PRELIMINARY_WAVELET_BCH_CONFIG
    )


if __name__ == "__main__":
    main()