from research.config import (
    EQUAL_DECODER_SMOKE_CONFIG,
    EQUAL_DECODER_20K_CONFIG,
)

from research.runner import run_research


# False -> быстрый проверочный прогон
# True  -> основной эксперимент на 20 000 сообщений
RUN_FULL = True


def main() -> None:
    config = (
        EQUAL_DECODER_20K_CONFIG
        if RUN_FULL
        else EQUAL_DECODER_SMOKE_CONFIG
    )

    print("=" * 70)
    print("Equal-decoder Wavelet vs BCH-derived comparison")
    print("=" * 70)

    for code in config.codes:
        print()
        print(code.name)
        print(
            "  syndrome t =",
            code.syndrome_max_error_weight,
        )
        print(
            "  Chase inner t =",
            code.chase_inner_decoder_max_error_weight,
        )
        print(
            "  Chase p =",
            code.chase_unreliable_positions_count,
        )

    print()
    print("=" * 70)

    run_research(config)


if __name__ == "__main__":
    main()