from research.config import COMPARE_64_32_SMOKE_CONFIG
from research.runner import run_research


def main() -> None:
    """
    Smoke‑сравнение кодов:
        Wavelet [64,32]
        BCH-derived [64,32]
        Goppa-derived [64,32]
    У всех кодов одинаковые настройки:
        syndrome t=3
        Chase t=3, p=8
    """
    run_research(COMPARE_64_32_SMOKE_CONFIG)


if __name__ == "__main__":
    main()
