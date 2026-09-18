"""Короткий fair-comparison запуск Wavelet, BCH-derived, Goppa-derived и RS binary."""

from research.config import FOUR_FAMILIES_SMOKE_CONFIG
from research.runner import run_research


def main() -> None:
    """Запускает 4 семейства [16,8] с общими сообщениями, шумом и syndrome decoder."""
    run_research(FOUR_FAMILIES_SMOKE_CONFIG)


if __name__ == "__main__":
    main()
