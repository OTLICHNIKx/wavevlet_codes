from research.config import COMPARE_16_8_SMOKE_CONFIG
from research.runner import run_research


def main() -> None:
    """
    Smoke-тест для сравнения [16,8] кодов.

    Запускает:
        Wavelet [16,8]
        BCH-derived [16,8] (BCH(31,21,5) -> shorten 13 -> [18,8] -> puncture (8,10))
    """
    run_research(COMPARE_16_8_SMOKE_CONFIG)


if __name__ == "__main__":
    main()
