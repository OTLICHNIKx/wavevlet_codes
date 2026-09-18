from research.code_factory import build_code_from_config
from research.config import BCH_DERIVED_16_8_CONFIG
from research.distance_analysis import (
    analyze_small_code,
    format_small_code_analysis,
)


def main() -> None:
    code = build_code_from_config(
        BCH_DERIVED_16_8_CONFIG
    )

    print("=" * 70)
    print("BCH-derived [16,8] final verification")
    print("=" * 70)

    print("n =", code.n)
    print("k =", code.k)

    print(
        "parent =",
        (
            code.parent_code.n,
            code.parent_code.k,
            code.parent_code.designed_distance,
        ),
    )

    print(
        "punctured parent coordinates =",
        code.punctured_parent_coordinates,
    )

    analysis = analyze_small_code(
        generator_matrix=code.generator_matrix,
        parity_check_matrix=code.parity_check_matrix,
    )

    print()
    print(format_small_code_analysis(analysis))

    print()

    assert code.n == 16
    assert code.k == 8
    assert analysis.d_min == 5
    assert analysis.minimum_weight_count == 24

    expected_weight_enumerator = (
        1,
        0,
        0,
        0,
        0,
        24,
        44,
        40,
        45,
        40,
        28,
        24,
        10,
        0,
        0,
        0,
        0,
    )

    assert (
        analysis.weight_enumerator
        == expected_weight_enumerator
    )

    print("OK: BCH-derived [16,8,5] построен правильно.")


if __name__ == "__main__":
    main()