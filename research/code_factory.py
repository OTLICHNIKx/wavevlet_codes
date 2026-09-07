import numpy as np

from bch import BCHCode, BCHDerivedCode
from goppa import GoppaDerivedCode
from reed_solomon import ReedSolomonBinaryCode
from goppa.presets import (
    GOPPA_16_8_CODE,
    GOPPA_32_16_CODE,
    GOPPA_64_32_CODE,
)
from wavelet import WaveletCode

from research.config import CodeResearchConfig


ResearchCode = (
    WaveletCode
    | BCHCode
    | BCHDerivedCode
    | GoppaDerivedCode
    | ReedSolomonBinaryCode
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
            puncture_coordinates=(
                code_config.bch_puncture_coordinates
            ),
            name=code_config.name,
        )

    elif code_config.family == "reed_solomon_binary":
        required_values = {
            "reed_solomon_m": code_config.reed_solomon_m,
            "reed_solomon_symbol_n": (
                code_config.reed_solomon_symbol_n
            ),
            "reed_solomon_symbol_k": (
                code_config.reed_solomon_symbol_k
            ),
        }
        missing_fields = [
            name for name, value in required_values.items()
            if value is None
        ]
        if missing_fields:
            raise ValueError(
                "Для reed_solomon_binary отсутствуют параметры: "
                + ", ".join(missing_fields)
            )
        code = ReedSolomonBinaryCode.from_parameters(
            m=code_config.reed_solomon_m,
            symbol_n=code_config.reed_solomon_symbol_n,
            symbol_k=code_config.reed_solomon_symbol_k,
            primitive_polynomial=(
                code_config.reed_solomon_primitive_polynomial
            ),
            evaluation_points=(
                code_config.reed_solomon_evaluation_points
            ),
            column_multipliers=(
                code_config.reed_solomon_column_multipliers
            ),
            name=code_config.name,
        )
    elif code_config.family == "goppa_derived":
        if code_config.goppa_m is None:
            raise ValueError(
                "Для Goppa-кода отсутствует goppa_m"
            )

        if code_config.goppa_degree is None:
            raise ValueError(
                "Для Goppa-кода отсутствует goppa_degree"
            )

        # Используем пресеты для воспроизводимости
        if code_config.n == 16 and code_config.k == 8:
            code = GOPPA_16_8_CODE
        elif code_config.n == 32 and code_config.k == 16:
            code = GOPPA_32_16_CODE
        elif code_config.n == 64 and code_config.k == 32:
            code = GOPPA_64_32_CODE
        else:
            raise ValueError(
                f"Для Goppa-derived нет пресета для ({code_config.n}, {code_config.k}). "
                "Используйте пресеты или добавьте новый."
            )

        # Пресет фиксирован по (n, k), но goppa_m/goppa_degree/goppa_seed
        # в конфиге должны совпадать с параметрами этого пресета, иначе
        # реально построенный код будет отличаться от того, что описан
        # в конфигурации (и, соответственно, в summary.csv).
        construction = code.parent_code.construction
        mismatches: list[str] = []

        if construction.m != code_config.goppa_m:
            mismatches.append(
                f"goppa_m: конфиг={code_config.goppa_m}, "
                f"пресет={construction.m}"
            )

        if construction.degree != code_config.goppa_degree:
            mismatches.append(
                f"goppa_degree: конфиг={code_config.goppa_degree}, "
                f"пресет={construction.degree}"
            )

        if construction.seed != code_config.goppa_seed:
            mismatches.append(
                f"goppa_seed: конфиг={code_config.goppa_seed}, "
                f"пресет={construction.seed}"
            )

        if mismatches:
            raise ValueError(
                "Параметры goppa_derived в конфиге не совпадают с "
                f"зафиксированным пресетом ({code_config.n}, {code_config.k}): "
                + "; ".join(mismatches)
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
