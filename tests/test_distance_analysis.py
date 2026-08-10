import numpy as np
import pytest

from research.distance_analysis import (
    SmallCodeAnalysis,
    analyze_small_code,
    format_small_code_analysis,
)


def test_analyze_small_code_wavelet_16_8() -> None:
    """
    Проверяем полный анализ Wavelet [16,8] (256 кодовых слов).
    d_min должен быть 5 (см. research/check_min_distance_64_32.py и ТЗ §1.1).
    """
    from research.code_factory import build_code_from_config
    from research.config import WAVELET_16_8_CONFIG

    code = build_code_from_config(WAVELET_16_8_CONFIG)
    analysis = analyze_small_code(
        code.generator_matrix,
        code.parity_check_matrix,
    )

    # Структурные свойства.
    assert analysis.k == 8
    assert analysis.n == 16
    assert analysis.d_min == 5
    assert analysis.minimum_weight_count > 0

    # Всего должно быть ровно 256 кодовых слов (2^8).
    assert sum(analysis.weight_enumerator) == 256

    # Нулевое слово всегда имеет вес 0 (должно быть ровно одно).
    assert analysis.weight_enumerator[0] == 1


def test_analyze_small_code_negative_k() -> None:
    """k > 16 не поддерживается — должен быть ValueError."""
    rng = np.random.default_rng(42)

    bad_gen = rng.integers(0, 2, size=(17, 17), dtype=np.uint8)
    bad_gn, bad_h = bad_gen, rng.integers(0, 2, size=(4, 17), dtype=np.uint8)

    with pytest.raises(ValueError, match="k <= 16"):
        analyze_small_code(bad_gn, bad_h)


def test_analyze_small_code_invalid_rank() -> None:
    """Матрица без полного ранга должна отклоняться."""
    gen = np.array(
        [
            [1, 0, 0, 0],
            [0, 0, 0, 0],  # нулевая строка -> rank < k
        ],
        dtype=np.uint8,
    )
    h = np.array(
        [
            [1, 1, 1, 1],
            [0, 1, 0, 1],
        ],
        dtype=np.uint8,
    )

    with pytest.raises(ValueError, match="полный строковый ранг"):
        analyze_small_code(gen, h)


def test_small_code_analysis_formatting() -> None:
    """Проверяем, что human-readable формат не падает."""
    from research.code_factory import build_code_from_config
    from research.config import WAVELET_16_8_CONFIG

    code = build_code_from_config(WAVELET_16_8_CONFIG)
    analysis = analyze_small_code(
        code.generator_matrix,
        code.parity_check_matrix,
    )
    text = format_small_code_analysis(analysis)
    assert "Код: [16, 8]" in text
    assert "d_min = 5" in text
