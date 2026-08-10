import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal


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

    # Устаревшее поле для обратной совместимости.
    expected_min_distance: int | None = None

    # Актуальные метаданные по расстоянию.
    minimum_distance_exact: int | None = None
    minimum_distance_lower_bound: int | None = None
    minimum_distance_upper_bound: int | None = None
    distance_evidence: str = ""
    verified_error_correction_radius: int | None = None

    syndrome_max_error_weight: int | None = None
    chase_inner_decoder_max_error_weight: int | None = None
    chase_unreliable_positions_count: int | None = None

    def to_json_dict(self) -> dict[str, Any]:
        """Сериализует конфиг в JSON-совместимый словарь."""
        return {
            "name": self.name,
            "n": self.n,
            "k": self.k,

            "family": self.family,

            # Параметры wavelet.
            "h": None if self.h is None else list(self.h),
            "g": None if self.g is None else list(self.g),
            "a": self.a,
            "b": self.b,
            "shift": self.shift,

            # Параметры BCH.
            "bch_m": self.bch_m,
            "bch_designed_distance": self.bch_designed_distance,
            "bch_primitive_polynomial": self.bch_primitive_polynomial,
            "bch_first_root": self.bch_first_root,

            "bch_shortening_count": self.bch_shortening_count,
            "bch_puncture_count": self.bch_puncture_count,

            # Устаревшее поле.
            "expected_min_distance": self.expected_min_distance,

            # Новые метаданные по расстоянию.
            "minimum_distance_exact": self.minimum_distance_exact,
            "minimum_distance_lower_bound": self.minimum_distance_lower_bound,
            "minimum_distance_upper_bound": self.minimum_distance_upper_bound,
            "distance_evidence": self.distance_evidence,
            "verified_error_correction_radius": self.verified_error_correction_radius,

            # Декодер overrides.
            "syndrome_max_error_weight": self.syndrome_max_error_weight,
            "chase_inner_decoder_max_error_weight": (
                self.chase_inner_decoder_max_error_weight
            ),
            "chase_unreliable_positions_count": (
                self.chase_unreliable_positions_count
            ),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "CodeResearchConfig":
        """Десериализует конфиг из JSON-совместимого словаря."""
        converted = data.copy()

        for key in ("h", "g"):
            if converted.get(key) is not None:
                converted[key] = tuple(int(v) for v in converted[key])

        if "family" in converted:
            converted["family"] = str(converted["family"])

        return cls(**converted)

    def __post_init__(self) -> None:
        if self.n <= 0:
            raise ValueError("n должно быть положительным")

        if self.k <= 0:
            raise ValueError("k должно быть положительным")

        if self.k >= self.n:
            raise ValueError("k должно быть меньше n")

        # Проверка согласованности метаданных расстояния.
        bounds = [
            v
            for v in (
                self.minimum_distance_exact,
                self.minimum_distance_lower_bound,
                self.minimum_distance_upper_bound,
                self.verified_error_correction_radius,
            )
            if v is not None
        ]

        if any(v < 0 for v in bounds):
            raise ValueError(
                "Значения расстояний и радиуса должны быть "
                "неотрицательными"
            )

        if self.minimum_distance_exact is not None:
            if (
                self.minimum_distance_lower_bound is not None
                and self.minimum_distance_exact
                < self.minimum_distance_lower_bound
            ):
                raise ValueError(
                    "minimum_distance_exact не может быть меньше "
                    "lower_bound"
                )
            if (
                self.minimum_distance_upper_bound is not None
                and self.minimum_distance_exact
                > self.minimum_distance_upper_bound
            ):
                raise ValueError(
                    "minimum_distance_exact не может быть больше "
                    "upper_bound"
                )

        if (
            self.minimum_distance_lower_bound is not None
            and self.minimum_distance_upper_bound is not None
            and self.minimum_distance_lower_bound
            > self.minimum_distance_upper_bound
        ):
            raise ValueError(
                "minimum_distance_lower_bound не может быть больше "
                "upper_bound"
            )

        if (
            self.verified_error_correction_radius is not None
            and self.minimum_distance_lower_bound is not None
        ):
            # t <= floor((d_min - 1) / 2)
            max_radius = (
                self.minimum_distance_lower_bound - 1
            ) // 2
            if self.verified_error_correction_radius > max_radius:
                raise ValueError(
                    "verified_error_correction_radius "
                    f"превышает допустимый радиус "
                    f"(d_min >= {self.minimum_distance_lower_bound} "
                    f"→ t <= {max_radius})"
                )

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

    def to_json_dict(self) -> dict[str, Any]:
        """Сериализует конфиг в JSON-совместимый словарь."""
        return asdict(self)

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "DecoderResearchConfig":
        """Десериализует конфиг из JSON-совместимого словаря."""
        return cls(**dict(data))


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

    def to_json_dict(self) -> dict[str, Any]:
        """Сериализует конфиг в JSON-совместимый словарь."""
        data = asdict(self)
        data["ebn0_db_values"] = list(self.ebn0_db_values)
        data["codes"] = [c.to_json_dict() for c in self.codes]
        data["decoders"] = self.decoders.to_json_dict()
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "ResearchConfig":
        """Десериализует конфиг из JSON-совместимого словаря."""
        converted = data.copy()

        converted["ebn0_db_values"] = tuple(
            float(v) for v in converted["ebn0_db_values"]
        )
        converted["codes"] = tuple(
            CodeResearchConfig.from_json_dict(c) for c in converted["codes"]
        )
        converted["decoders"] = DecoderResearchConfig.from_json_dict(
            converted["decoders"]
        )
        converted["results_dir"] = str(converted["results_dir"])

        return cls(**converted)

    def save_json(self, path: str | Path) -> None:
        """Сохраняет конфиг в JSON-файл."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load_json(cls, path: str | Path) -> "ResearchConfig":
        """Загружает конфиг из JSON-файла."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_json_dict(data)

    def estimate_workload(self) -> dict[str, int]:
        """Возвращает оценку объёма вычислений."""
        code_counts = {"chase_patterns": 0, "mld_codewords": 0}

        dec = self.decoders
        decoders_enabled = [
            dec.run_syndrome,
            dec.run_hard_mld,
            dec.run_soft_mld,
            dec.run_chase,
        ]
        num_decoders = sum(bool(d) for d in decoders_enabled)

        for code in self.codes:
            chase_p = (
                code.chase_unreliable_positions_count
                if code.chase_unreliable_positions_count is not None
                else dec.chase_unreliable_positions_count
            )
            code_counts["chase_patterns"] += 2 ** chase_p
            if dec.run_hard_mld or dec.run_soft_mld:
                if code.k <= dec.max_k_for_mld:
                    code_counts["mld_codewords"] += 2 ** code.k

        return {
            "code_count": len(self.codes),
            "decoder_count": num_decoders,
            "ebn0_point_count": len(self.ebn0_db_values),
            "message_count": self.message_count,
            "total_series": len(self.codes) * num_decoders * len(self.ebn0_db_values),
            "total_frames": len(self.codes) * num_decoders * len(self.ebn0_db_values)
            * self.message_count,
            "chase_patterns_total": code_counts["chase_patterns"],
            "mld_codewords_total": code_counts["mld_codewords"],
        }


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

    # Проверено: все ошибки веса <= 3 имеют разные синдромы,
    # и найдено кодовое слово веса 8. Текущая строгая граница:
    # 7 <= d_min <= 8; точное d_min отдельно не доказано.
    expected_min_distance=None,

    # Проверенная уникальность синдромов до веса 3 позволяет
    # использовать гарантированный радиус t=3.
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

    # Для BCH родительского кода гарантированная нижняя граница
    # задаётся как designed_distance. Для derived код применяем
    # выравнивание по puncture/shortening через специальные поля.
    expected_min_distance=None,
    minimum_distance_exact=None,
    minimum_distance_lower_bound=7,
    minimum_distance_upper_bound=None,
    distance_evidence="designed distance (lower bound) via BCH",
    verified_error_correction_radius=3,

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
    minimum_distance_exact=None,
    minimum_distance_lower_bound=9,
    minimum_distance_upper_bound=None,
    distance_evidence=(
        "BCH-derived [127,92,d>=11] -> shorten 60 -> [67,32] "
        "-> puncture 3 -> [64,32]; d_min >= 8 via construction, "
        "verified >= 9 via syndrome table (no collisions weight <= 4)"
    ),
    verified_error_correction_radius=4,

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


BCH_DERIVED_16_8_CONFIG = CodeResearchConfig(
    name="bch_derived_16_8",
    family="bch_derived",

    n=16,
    k=8,

    bch_m=5,
    bch_designed_distance=5,
    bch_first_root=1,

    # [31,21,5] -> shorten 13 -> [18,8] -> puncture 2 -> [16,8]
    bch_shortening_count=13,
    bch_puncture_count=2,

    # Explicit puncture coordinates (found optimal).
    # See research/find_best_bch_16_8.py
    expected_min_distance=None,
    minimum_distance_exact=None,
    minimum_distance_lower_bound=4,
    minimum_distance_upper_bound=None,
    distance_evidence="exhaustive search over C(18,2) puncturing pairs",
    verified_error_correction_radius=1,  # t = floor((4-1)/2) = 1

    syndrome_max_error_weight=1,
    chase_inner_decoder_max_error_weight=1,
    chase_unreliable_positions_count=3,
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


BCH_DERIVED_32_16_CONFIG = CodeResearchConfig(
    name="bch_derived_32_16",
    family="bch_derived",

    n=32,
    k=16,

    bch_m=6,
    bch_designed_distance=7,
    bch_first_root=1,

    # [63,45] -> [34,16] -> [32,16]
    bch_shortening_count=29,
    bch_puncture_count=2,

    expected_min_distance=None,
    minimum_distance_exact=None,
    minimum_distance_lower_bound=5,
    minimum_distance_upper_bound=None,
    distance_evidence="BCH(63,45,d>=7) shorten 29 puncture 2",
    verified_error_correction_radius=2,

    syndrome_max_error_weight=2,
    chase_inner_decoder_max_error_weight=2,
    chase_unreliable_positions_count=5,
)


COMPARE_16_8_SMOKE_CONFIG = ResearchConfig(
    message_count=500,
    message_seed=12345,
    noise_seed=54321,
    ebn0_db_values=(0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0),
    codes=(
        WAVELET_16_8_CONFIG,
        BCH_DERIVED_16_8_CONFIG,
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
    results_dir="research_results/compare_16_8/smoke",
)


COMPARE_32_16_SMOKE_CONFIG = ResearchConfig(
    message_count=500,
    message_seed=12345,
    noise_seed=54321,
    ebn0_db_values=(0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0),
    codes=(
        WAVELET_32_16_CONFIG,
        BCH_DERIVED_32_16_CONFIG,
    ),
    decoders=DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=True,
        run_soft_mld=True,
        run_chase=True,
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=2,
        chase_unreliable_positions_count=5,
        max_k_for_mld=16,
    ),
    results_dir="research_results/compare_32_16/smoke",
)


FINAL_20K_PRESET = ResearchConfig(
    message_count=20_000,
    message_seed=12345,
    noise_seed=54321,
    ebn0_db_values=(0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0),
    codes=(
        # Wavelet
        WAVELET_64_32_CONFIG,
        WAVELET_16_8_CONFIG,
        WAVELET_32_16_CONFIG,
        # BCH
        BCH_63_45_CONFIG,
        BCH_DERIVED_64_32_CONFIG,
        BCH_DERIVED_16_8_CONFIG,
        BCH_DERIVED_32_16_CONFIG,
    ),
    decoders=DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=True,
        run_soft_mld=True,
        run_chase=True,
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=2,
        chase_unreliable_positions_count=5,
        max_k_for_mld=16,
    ),
    results_dir="research_results/final_20000",
)
