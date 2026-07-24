import numpy as np

from bch import BCHCode, BCHDerivedCode
from wavelet import WaveletCode

from research.config import CodeResearchConfig


ResearchCode = (
    WaveletCode
    | BCHCode
    | BCHDerivedCode
)


def validate_research_code(
    code: ResearchCode,
    config: CodeResearchConfig,
) -> None:
    """
    Проверяет, что построенный код соответствует конфигурации
    и пригоден для существующих декодеров.
    """
    if code.n != config.n:
        raise ValueError(
            f"Ожидалось n = {config.n}, "
            f"но построен код n = {code.n}"
        )

    if code.k != config.k:
        raise ValueError(
            f"Ожидалось k = {config.k}, "
            f"но построен код k = {code.k}"
        )

    generator_matrix = np.asarray(
        code.generator_matrix,
        dtype=np.uint8,
    )

    parity_check_matrix = np.asarray(
        code.parity_check_matrix,
        dtype=np.uint8,
    )

    if generator_matrix.shape != (
        config.k,
        config.n,
    ):
        raise ValueError(
            "Неверный размер generator_matrix: "
            f"{generator_matrix.shape}"
        )

    if parity_check_matrix.shape != (
        config.n - config.k,
        config.n,
    ):
        raise ValueError(
            "Неверный размер parity_check_matrix: "
            f"{parity_check_matrix.shape}"
        )

    product = (
        generator_matrix.astype(np.int64)
        @ parity_check_matrix.astype(np.int64).T
    ) % 2

    if not np.all(product == 0):
        raise ValueError(
            "Матрицы кода не согласованы: "
            "G @ H.T должно быть равно нулю"
        )


def build_code_from_config(
    code_config: CodeResearchConfig,
) -> ResearchCode:
    """
    Строит WaveletCode, BCHCode или BCHDerivedCode
    по общей конфигурации.
    """
    if code_config.family == "wavelet":
        if code_config.h is None:
            raise ValueError(
                "Для wavelet-кода отсутствует h"
            )

        code: ResearchCode = (
            WaveletCode.from_scaling_coefficients(
                h=code_config.h,
                g=code_config.g,
                codeword_length=code_config.n,
                field=2,
                a=code_config.a,
                b=code_config.b,
                shift=code_config.shift,
                name=code_config.name,
            )
        )

    elif code_config.family == "bch":
        if code_config.bch_m is None:
            raise ValueError(
                "Для BCH-кода отсутствует bch_m"
            )

        if code_config.bch_designed_distance is None:
            raise ValueError(
                "Для BCH-кода отсутствует "
                "bch_designed_distance"
            )

        code = BCHCode.primitive(
            m=code_config.bch_m,
            designed_distance=(
                code_config.bch_designed_distance
            ),
            primitive_polynomial=(
                code_config.bch_primitive_polynomial
            ),
            first_root=code_config.bch_first_root,
            name=code_config.name,
        )

    elif code_config.family == "bch_derived":
        if code_config.bch_m is None:
            raise ValueError(
                "Для bch_derived отсутствует bch_m"
            )

        if code_config.bch_designed_distance is None:
            raise ValueError(
                "Для bch_derived отсутствует "
                "bch_designed_distance"
            )

        if code_config.bch_shortening_count is None:
            raise ValueError(
                "Для bch_derived отсутствует "
                "bch_shortening_count"
            )

        if code_config.bch_puncture_count is None:
            raise ValueError(
                "Для bch_derived отсутствует "
                "bch_puncture_count"
            )

        code = BCHDerivedCode.from_primitive_parent(
            m=code_config.bch_m,
            designed_distance=(
                code_config.bch_designed_distance
            ),
            primitive_polynomial=(
                code_config.bch_primitive_polynomial
            ),
            first_root=code_config.bch_first_root,
            shortening_count=(
                code_config.bch_shortening_count
            ),
            puncture_count=(
                code_config.bch_puncture_count
            ),
            name=code_config.name,
        )

    else:
        raise ValueError(
            "Неизвестное семейство кода: "
            f"{code_config.family}"
        )

    validate_research_code(
        code=code,
        config=code_config,
    )

    return code