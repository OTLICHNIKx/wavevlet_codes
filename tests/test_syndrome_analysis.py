import numpy as np
import pytest

from bch.derived import BCHDerivedCode

from bch.syndrome_analysis import (
    analyze_syndrome_collisions,
    count_error_patterns,
)


@pytest.fixture(scope="module")
def derived_code() -> BCHDerivedCode:
    return BCHDerivedCode.from_primitive_parent(
        m=7,
        designed_distance=11,
        shortening_count=60,
        puncture_count=3,
        name="bch_derived_64_32",
    )


def test_error_pattern_counts() -> None:
    assert count_error_patterns(
        codeword_length=64,
        max_error_weight=3,
    ) == 43_745

    assert count_error_patterns(
        codeword_length=64,
        max_error_weight=4,
    ) == 679_121


def test_detects_simple_syndrome_collision() -> None:
    """
    Первые два столбца одинаковые.

    Поэтому одиночные ошибки в позициях 0 и 1
    имеют одинаковый синдром.
    """
    parity_check_matrix = np.asarray(
        [
            [1, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.uint8,
    )

    analysis = analyze_syndrome_collisions(
        parity_check_matrix=parity_check_matrix,
        max_error_weight=1,
        stop_after_first_collision=True,
    )

    assert not analysis.collision_free
    assert analysis.first_collision is not None

    collision = analysis.first_collision

    assert collision.first_error_positions == (0,)
    assert collision.second_error_positions == (1,)

    assert collision.codeword_positions == (0, 1)
    assert collision.codeword_weight == 2


def test_bch_derived_64_32_has_no_collisions_up_to_weight_3(
    derived_code: BCHDerivedCode,
) -> None:
    analysis = analyze_syndrome_collisions(
        parity_check_matrix=(
            derived_code.parity_check_matrix
        ),
        max_error_weight=3,
    )

    assert analysis.completed
    assert analysis.collision_free

    assert analysis.tested_pattern_count == 43_745
    assert analysis.unique_syndrome_count == 43_745

    assert (
        analysis
        .guaranteed_minimum_distance_lower_bound
        == 7
    )

    assert analysis.guaranteed_error_correction == 3