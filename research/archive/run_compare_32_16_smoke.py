from research.config import COMPARE_32_16_SMOKE_CONFIG
from research.runner import run_research


def main() -> None:
    """
    Smoke-тест для сравнения [32,16] кодов.

    Запускает:
        Wavelet [32,16]
        BCH-derived [32,16] (BCH(63,45,7) -> shorten 29 -> [34,16] -> puncture 2)
    """
    run_research(COMPARE_32_16_SMOKE_CONFIG)


if __name__ == "__main__":
    main()
