from research.config import DEFAULT_RESEARCH_CONFIG
from research.h_search import exact_min_distance
from research.runner import build_code_from_config


def main() -> None:
    for code_config in DEFAULT_RESEARCH_CONFIG.codes:
        if code_config.k > 16:
            print()
            print(f"{code_config.name}: пропуск точного d_min, k={code_config.k}")
            continue

        print()
        print("=" * 70)
        print(f"Проверка {code_config.name}")
        print("n =", code_config.n)
        print("k =", code_config.k)
        print("h =", code_config.h)
        print("g =", code_config.g)
        print("expected_min_distance =", code_config.expected_min_distance)

        code = build_code_from_config(code_config)

        d_min = exact_min_distance(code.generator_matrix)

        print("calculated d_min =", d_min)

        if code_config.expected_min_distance is not None:
            if d_min == code_config.expected_min_distance:
                print("OK: d_min совпадает")
            else:
                print("WARNING: d_min не совпадает")


if __name__ == "__main__":
    main()