from time import perf_counter

from decode.syndrome_decoding import (
    build_compact_syndrome_table,
)
from research.code_factory import build_code_from_config
from research.config import (
    BCH_DERIVED_64_32_CONFIG,
    WAVELET_64_32_CONFIG,
)


def check_code(label: str, code_config, t: int) -> None:
    code = build_code_from_config(code_config)

    start = perf_counter()
    table = build_compact_syndrome_table(
        parity_check_matrix=code.parity_check_matrix,
        max_error_weight=t,
    )
    elapsed = perf_counter() - start

    print(label)
    print(f"  n={code.n}, k={code.k}, t={t}")
    print(f"  patterns={table.pattern_count}")
    print(f"  entries={table.entry_count}")
    print(f"  collisions={table.collision_count}")
    print(
        "  approx_memory_mib="
        f"{table.approx_memory_bytes / (1024 ** 2):.2f}"
    )
    print(f"  build_time_sec={elapsed:.3f}")
    print()


def main() -> None:
    check_code(
        "Wavelet [64,32]",
        WAVELET_64_32_CONFIG,
        t=3,
    )

    check_code(
        "BCH-derived [64,32]",
        BCH_DERIVED_64_32_CONFIG,
        t=4,
    )


if __name__ == "__main__":
    main()
