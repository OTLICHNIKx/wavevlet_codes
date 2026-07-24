from dataclasses import dataclass, replace
from typing import Literal


CodeFamily = Literal[
    "wavelet",
    "bch",
    "bch_derived",
]


@dataclass(frozen=True)
class CodeResearchConfig:
    """
    Настройки одного исследуемого линейного кода.
    """

    name: str
    n: int
    k: int

    family: CodeFamily = "wavelet"

    # Настройки вейвлет-кода.
    h: tuple[int, ...] | None = None
    g: tuple[int, ...] | None = None

    a: int = 1
    b: int = 1
    shift: int = 1

    # Настройки примитивного BCH-кода.
    bch_m: int | None = None
    bch_designed_distance: int | None = None
    bch_primitive_polynomial: int | None = None
    bch_first_root: int = 1

    bch_shortening_count: int | None = None
    bch_puncture_count: int | None = None

    expected_min_distance: int | None = None

    syndrome_max_error_weight: int | None = None
    chase_inner_decoder_max_error_weight: int | None = None
    chase_unreliable_positions_count: int | None = None

    def __post_init__(self) -> None:
        if self.n <= 0:
            raise ValueError("n должно быть положительным")

        if self.k <= 0:
            raise ValueError("k должно быть положительным")

        if self.k >= self.n:
            raise ValueError("k должно быть меньше n")

        if self.family == "wavelet":
            if self.h is None or len(self.h) == 0:
                raise ValueError(
                    "Для wavelet-кода необходимо задать h"
                )

        elif self.family == "bch":
            if self.bch_m is None:
                raise ValueError(
                    "Для BCH-кода необходимо задать bch_m"
                )

            if self.bch_designed_distance is None:
                raise ValueError(
                    "Для BCH-кода необходимо задать "
                    "bch_designed_distance"
                )

            expected_length = (1 << self.bch_m) - 1

            if self.n != expected_length:
                raise ValueError(
                    "Для примитивного BCH-кода ожидается "
                    f"n = 2^{self.bch_m} - 1 = "
                    f"{expected_length}, получено n = {self.n}"
                )

        elif self.family == "bch_derived":
            required_values = {
                "bch_m": self.bch_m,
                "bch_designed_distance": (
                    self.bch_designed_distance
                ),
                "bch_shortening_count": (
                    self.bch_shortening_count
                ),
                "bch_puncture_count": (
                    self.bch_puncture_count
                ),
            }

            missing_fields = [
                name
                for name, value in required_values.items()
                if value is None
            ]

            if missing_fields:
                raise ValueError(
                    "Для bch_derived не заданы параметры: "
                    + ", ".join(missing_fields)
                )

            # После проверки выше эти значения точно не None.
            assert self.bch_m is not None
            assert self.bch_shortening_count is not None
            assert self.bch_puncture_count is not None

            if self.bch_shortening_count < 0:
                raise ValueError(
                    "bch_shortening_count "
                    "не может быть отрицательным"
                )

            if self.bch_puncture_count < 0:
                raise ValueError(
                    "bch_puncture_count "
                    "не может быть отрицательным"
                )

            parent_length = (1 << self.bch_m) - 1

            expected_length = (
                    parent_length
                    - self.bch_shortening_count
                    - self.bch_puncture_count
            )

            if self.n != expected_length:
                raise ValueError(
                    "Длина BCH-derived кода не соответствует "
                    "родительской длине, укорочению и выкалыванию: "
                    f"ожидалось n={expected_length}, "
                    f"указано n={self.n}"
                )

        else:
            raise ValueError(
                f"Неизвестное семейство кода: {self.family}"
            )


@dataclass(frozen=True)
class DecoderResearchConfig:
    """
    Настройки декодеров.
    """

    syndrome_max_error_weight: int = 2
    chase_unreliable_positions_count: int = 4
    chase_inner_decoder_max_error_weight: int = 2

    run_syndrome: bool = True
    run_hard_mld: bool = True
    run_soft_mld: bool = True
    run_chase: bool = True

    # Полный MLD имеет сложность 2^k.
    max_k_for_mld: int = 16


@dataclass(frozen=True)
class ResearchConfig:
    """
    Общие настройки исследования.
    """

    message_count: int
    message_seed: int
    noise_seed: int

    ebn0_db_values: tuple[float, ...]

    codes: tuple[CodeResearchConfig, ...]
    decoders: DecoderResearchConfig

    results_dir: str


WAVELET_16_8_CONFIG = CodeResearchConfig(
    name="wavelet_16_8",
    family="wavelet",
    n=16,
    k=8,
    h=(1, 0, 0, 1, 0, 1, 0),
    g=(1, 1, 1, 1, 0, 1, 1),
    expected_min_distance=5,
    syndrome_max_error_weight=2,
    chase_inner_decoder_max_error_weight=2,
    chase_unreliable_positions_count=4,
)


WAVELET_32_16_CONFIG = CodeResearchConfig(
    name="wavelet_32_16",
    family="wavelet",
    n=32,
    k=16,
    h=(1, 0, 0, 0, 0, 0, 0, 0, 1, 1),
    g=(0, 1, 0, 0, 1, 1, 0, 1, 0, 1),
    expected_min_distance=8,
    syndrome_max_error_weight=3,
    chase_inner_decoder_max_error_weight=3,
    chase_unreliable_positions_count=6,
)


WAVELET_64_32_CONFIG = CodeResearchConfig(
    name="wavelet_64_32",
    family="wavelet",
    n=64,
    k=32,
    h=(
        1, 0, 0, 1, 0, 0, 1, 1,
        1, 1, 0, 0, 0, 1, 0, 0,
        1, 1, 1, 1, 1, 0, 1, 0,
        0, 0, 1, 1, 1, 1, 1, 1,
    ),
    g=None,

    # Для этой матрицы ранее нашли d_min = 8.
    expected_min_distance=8,

    # При d_min = 8 гарантированное уникальное исправление:
    # floor((8 - 1) / 2) = 3.
    syndrome_max_error_weight=3,
    chase_inner_decoder_max_error_weight=3,
    chase_unreliable_positions_count=8,
)


BCH_15_7_CONFIG = CodeResearchConfig(
    name="bch_15_7_delta_5",
    family="bch",
    n=15,
    k=7,
    bch_m=4,
    bch_designed_distance=5,
    bch_first_root=1,
    expected_min_distance=5,
    syndrome_max_error_weight=2,
    chase_inner_decoder_max_error_weight=2,
    chase_unreliable_positions_count=4,
)


BCH_63_45_CONFIG = CodeResearchConfig(
    name="bch_63_45_delta_7",
    family="bch",
    n=63,
    k=45,
    bch_m=6,
    bch_designed_distance=7,
    bch_first_root=1,

    # Для BCH это гарантированная нижняя граница:
    # d_min >= designed_distance.
    expected_min_distance=7,

    syndrome_max_error_weight=3,
    chase_inner_decoder_max_error_weight=3,

    # Для первого теста используем p=6:
    # Chase проверит 2^6 = 64 шаблона на слово.
    chase_unreliable_positions_count=6,
)

BCH_DERIVED_64_32_CONFIG = CodeResearchConfig(
    name="bch_derived_64_32",
    family="bch_derived",

    n=64,
    k=32,

    # Родительский примитивный BCH [127,92,d>=11].
    bch_m=7,
    bch_designed_distance=11,
    bch_first_root=1,

    # [127,92] -> [67,32] -> [64,32].
    bch_shortening_count=60,
    bch_puncture_count=3,

    # Точное d_min пока не установлено.
    # Проверено только d_min >= 9.
    expected_min_distance=None,

    # Для основного честного сравнения используем
    # одинаковый радиус t=3.
    syndrome_max_error_weight=3,
    chase_inner_decoder_max_error_weight=3,
    chase_unreliable_positions_count=6,
)


DEFAULT_RESEARCH_CONFIG = ResearchConfig(
    message_count=10_000,

    message_seed=12345,
    noise_seed=54321,

    ebn0_db_values=(
        0.0,
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
    ),

    codes=(
        WAVELET_16_8_CONFIG,
        WAVELET_32_16_CONFIG,
        WAVELET_64_32_CONFIG,
    ),

    decoders=DecoderResearchConfig(
        syndrome_max_error_weight=2,
        chase_unreliable_positions_count=4,
        chase_inner_decoder_max_error_weight=2,
        run_syndrome=True,
        run_hard_mld=True,
        run_soft_mld=True,
        run_chase=True,
        max_k_for_mld=16,
    ),

    results_dir="research_results",
)


BCH_SMOKE_RESEARCH_CONFIG = ResearchConfig(
    # Небольшой запуск для проверки интеграции.
    message_count=50,

    message_seed=12345,
    noise_seed=54321,

    ebn0_db_values=(2.0,),

    codes=(
        WAVELET_16_8_CONFIG,
        BCH_15_7_CONFIG,
        WAVELET_64_32_CONFIG,
        BCH_63_45_CONFIG,
    ),

    decoders=DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=True,
        run_soft_mld=True,
        run_chase=True,

        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=2,
        chase_unreliable_positions_count=4,

        max_k_for_mld=16,
    ),

    results_dir="research_results/bch_smoke",
)

WAVELET_64_32_PRELIMINARY_CONFIG = replace(
    WAVELET_64_32_CONFIG,
    name="wavelet_64_32_preliminary",

    # Для одинаковых условий Chase используем p=6
    # и для Wavelet, и для BCH.
    chase_unreliable_positions_count=6,
)


BCH_63_45_PRELIMINARY_CONFIG = replace(
    BCH_63_45_CONFIG,
    name="bch_63_45_preliminary",
    chase_unreliable_positions_count=6,
)


PRELIMINARY_WAVELET_BCH_CONFIG = ResearchConfig(
    message_count=500,

    message_seed=12345,
    noise_seed=54321,

    ebn0_db_values=(
        0.0,
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        4.5,
        5.0,
    ),

    codes=(
        WAVELET_64_32_PRELIMINARY_CONFIG,
        BCH_63_45_PRELIMINARY_CONFIG,
    ),

    decoders=DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=False,
        run_soft_mld=False,
        run_chase=True,

        syndrome_max_error_weight=3,
        chase_inner_decoder_max_error_weight=3,
        chase_unreliable_positions_count=6,

        max_k_for_mld=16,
    ),

    results_dir=(
        "research_results/"
        "preliminary_wavelet_bch"
    ),
)

WAVELET_64_32_EQUAL_T3_CONFIG = replace(
    WAVELET_64_32_CONFIG,

    name="wavelet_64_32_equal_t3",

    syndrome_max_error_weight=3,
    chase_inner_decoder_max_error_weight=3,
    chase_unreliable_positions_count=6,
)


BCH_DERIVED_64_32_EQUAL_T3_CONFIG = replace(
    BCH_DERIVED_64_32_CONFIG,

    name="bch_derived_64_32_equal_t3",

    syndrome_max_error_weight=3,
    chase_inner_decoder_max_error_weight=3,
    chase_unreliable_positions_count=6,
)


COMPARE_64_32_EQUAL_T3_SMOKE_CONFIG = ResearchConfig(
    message_count=500,

    message_seed=12345,
    noise_seed=54321,

    ebn0_db_values=(
        0.0,
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        4.5,
        5.0,
    ),

    codes=(
        WAVELET_64_32_EQUAL_T3_CONFIG,
        BCH_DERIVED_64_32_EQUAL_T3_CONFIG,
    ),

    decoders=DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=False,
        run_soft_mld=False,
        run_chase=True,

        syndrome_max_error_weight=3,
        chase_inner_decoder_max_error_weight=3,
        chase_unreliable_positions_count=6,

        max_k_for_mld=16,
    ),

    results_dir=(
        "research_results/"
        "compare_wavelet_bch_derived_64_32/"
        "equal_t3_smoke"
    ),
)