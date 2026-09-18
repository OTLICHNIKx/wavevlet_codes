import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from channel import CHANNEL_TYPES


CodeFamily = Literal[
    "wavelet",
    "bch",
    "bch_derived",
    "goppa_derived",
    "reed_solomon_binary",
    "ldpc",
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
    bch_puncture_coordinates: tuple[int, ...] | None = None

    # Настройки Goppa-derived кода.
    goppa_m: int | None = None
    goppa_degree: int | None = None
    goppa_support_size: int | None = None
    goppa_seed: int = 42
    goppa_primitive_polynomial: int | None = None
    # Для derivation_method="message_functional_kernel" (phase-2):
    # бинарный вектор-функционал на пространстве сообщений parent,
    # subcode = ker f. None = классический rref_first_k.
    goppa_subcode_functional: tuple[int, ...] | None = None
    # Параметры binary-image Reed-Solomon.
    reed_solomon_m: int | None = None
    reed_solomon_symbol_n: int | None = None
    reed_solomon_symbol_k: int | None = None
    reed_solomon_primitive_polynomial: int | None = None
    reed_solomon_evaluation_points: tuple[int, ...] | None = None
    reed_solomon_column_multipliers: tuple[int, ...] | None = None

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
            "bch_puncture_coordinates": (
                None
                if self.bch_puncture_coordinates is None
                else list(self.bch_puncture_coordinates)
            ),

            # Параметры Goppa.
            "goppa_m": self.goppa_m,
            "goppa_degree": self.goppa_degree,
            "goppa_support_size": self.goppa_support_size,
            "goppa_seed": self.goppa_seed,
            "goppa_primitive_polynomial": self.goppa_primitive_polynomial,
            "goppa_subcode_functional": (
                None
                if self.goppa_subcode_functional is None
                else list(self.goppa_subcode_functional)
            ),
            # Параметры Reed-Solomon.
            "reed_solomon_m": self.reed_solomon_m,
            "reed_solomon_symbol_n": self.reed_solomon_symbol_n,
            "reed_solomon_symbol_k": self.reed_solomon_symbol_k,
            "reed_solomon_primitive_polynomial": (
                self.reed_solomon_primitive_polynomial
            ),
            "reed_solomon_evaluation_points": (
                None if self.reed_solomon_evaluation_points is None
                else list(self.reed_solomon_evaluation_points)
            ),
            "reed_solomon_column_multipliers": (
                None if self.reed_solomon_column_multipliers is None
                else list(self.reed_solomon_column_multipliers)
            ),

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

        for key in (
            "reed_solomon_evaluation_points",
            "reed_solomon_column_multipliers",
        ):
            if converted.get(key) is not None:
                converted[key] = tuple(int(v) for v in converted[key])
        if converted.get("goppa_subcode_functional") is not None:
            converted["goppa_subcode_functional"] = tuple(
                int(v) for v in converted["goppa_subcode_functional"]
            )
        if converted.get("bch_puncture_coordinates") is not None:
            converted["bch_puncture_coordinates"] = tuple(
                int(v)
                for v in converted["bch_puncture_coordinates"]
            )

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

        elif self.family == "goppa_derived":
            if self.goppa_m is None:
                raise ValueError("Для goppa_derived необходимо задать goppa_m")
            if self.goppa_degree is None:
                raise ValueError("Для goppa_derived необходимо задать goppa_degree")
            if self.goppa_m <= 0 or self.goppa_degree <= 0:
                raise ValueError("goppa_m и goppa_degree должны быть положительными")
            if self.k > self.n:
                raise ValueError("k не может быть больше n")

        elif self.family == "reed_solomon_binary":
            required_values = {
                "reed_solomon_m": self.reed_solomon_m,
                "reed_solomon_symbol_n": self.reed_solomon_symbol_n,
                "reed_solomon_symbol_k": self.reed_solomon_symbol_k,
            }
            missing_fields = [
                name for name, value in required_values.items()
                if value is None
            ]
            if missing_fields:
                raise ValueError(
                    "Для reed_solomon_binary не заданы параметры: "
                    + ", ".join(missing_fields)
                )
            assert self.reed_solomon_m is not None
            assert self.reed_solomon_symbol_n is not None
            assert self.reed_solomon_symbol_k is not None
            if self.reed_solomon_m <= 0:
                raise ValueError("reed_solomon_m должно быть положительным")
            if not (0 < self.reed_solomon_symbol_k < self.reed_solomon_symbol_n):
                raise ValueError("Для RS требуется 0 < symbol_k < symbol_n")
            if self.reed_solomon_symbol_n > (1 << self.reed_solomon_m):
                raise ValueError("symbol_n не может превышать размер GF(2^m)")
            if self.n != self.reed_solomon_m * self.reed_solomon_symbol_n:
                raise ValueError("n не согласовано с RS symbol_n и m")
            if self.k != self.reed_solomon_m * self.reed_solomon_symbol_k:
                raise ValueError("k не согласовано с RS symbol_k и m")
            field_size = 1 << self.reed_solomon_m
            points = self.reed_solomon_evaluation_points
            if points is not None:
                if len(points) != self.reed_solomon_symbol_n:
                    raise ValueError("Число evaluation points должно совпадать с symbol_n")
                if len(set(points)) != len(points):
                    raise ValueError("Evaluation points GRS должны быть уникальны")
                if any(point < 0 or point >= field_size for point in points):
                    raise ValueError("Evaluation points должны принадлежать GF(2^m)")
            multipliers = self.reed_solomon_column_multipliers
            if multipliers is not None:
                if len(multipliers) != self.reed_solomon_symbol_n:
                    raise ValueError("Число column multipliers должно совпадать с symbol_n")
                if any(value <= 0 or value >= field_size for value in multipliers):
                    raise ValueError("Column multipliers должны быть ненулевыми элементами GF(2^m)")
        elif self.family == "ldpc":
            if (self.n, self.k) not in {(16, 8), (32, 16), (64, 32)}:
                raise ValueError(
                    "Для ldpc доступны только замороженные пресеты "
                    "(16, 8), (32, 16), (64, 32); "
                    f"получено (n={self.n}, k={self.k})"
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

    # Модель канала: awgn (историческое поведение по умолчанию),
    # rayleigh, sinusoidal, rayleigh_awgn (см. пакет channel/).
    channel_type: str = "awgn"
    channel_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.channel_type not in CHANNEL_TYPES:
            raise ValueError(
                f"Неизвестный канал: {self.channel_type!r}; "
                f"допустимы: {', '.join(CHANNEL_TYPES)}"
            )

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


# ============================================================
# Пресеты кодов и экспериментов.
#
# Данные хранятся в research/presets/{codes,experiments}/*.json
# (выгружены из прежних Python-констант). Загрузка ленивая:
# каждый пресет читается один раз и кэшируется в _PRESET_CACHE.
# Старые имена констант (например, WAVELET_16_8_CONFIG) работают
# через модульный __getattr__ ниже.
# ============================================================

_PRESETS_DIR = Path(__file__).resolve().parent / "presets"
_PRESET_CACHE: dict[str, object] = {}


def _load_preset(name: str) -> CodeResearchConfig | ResearchConfig:
    """Загружает пресет по имени из JSON-файла (с кэшированием)."""
    if name in _PRESET_CACHE:
        return _PRESET_CACHE[name]  # type: ignore[return-value]

    for subdirectory, key, factory in (
        ("codes", "code", CodeResearchConfig.from_json_dict),
        ("experiments", "experiment", ResearchConfig.from_json_dict),
    ):
        path = _PRESETS_DIR / subdirectory / f"{name}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            preset = factory(payload[key])
            _PRESET_CACHE[name] = preset
            return preset

    raise AttributeError(
        f"Неизвестный пресет research.config.{name}: "
        f"файл не найден в {_PRESETS_DIR}"
    )


def __getattr__(name: str):
    """PEP 562: ленивый доступ к пресетам по историческим именам."""
    if name.isupper() and (
        name.endswith("_CONFIG")
        or name.startswith(
            (
                "FOUR_FAMILIES_",
                "FIVE_FAMILIES_",
                "EQUAL_DECODER_",
                "EQUAL_NKR_",
                "FINAL_20K_",
            )
        )
    ):
        return _load_preset(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Константы и сборщики для сравнения каналов (не пресеты dataclass).

NEW_CHANNELS_SNR_DB = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
NEW_CHANNELS_MESSAGE_COUNT = 100
NEW_CHANNELS_SINUSOIDAL_PARAMS = {
    "amplitude": 0.5,
    "frequency": 0.125,
    "phase": 0.0,
}


def _new_channels_config(
    channel_type: str,
    results_dir: str,
    channel_params: dict[str, Any] | None = None,
) -> ResearchConfig:
    return ResearchConfig(
        message_count=NEW_CHANNELS_MESSAGE_COUNT,
        message_seed=12345,
        noise_seed=54321,
        ebn0_db_values=NEW_CHANNELS_SNR_DB,
        codes=_load_preset("FIVE_FAMILIES_20K_32_16").codes,  # type: ignore[union-attr]
        decoders=DecoderResearchConfig(
            run_syndrome=True,
            run_hard_mld=True,
            run_soft_mld=True,
            run_chase=True,
            syndrome_max_error_weight=2,
            chase_inner_decoder_max_error_weight=2,
            chase_unreliable_positions_count=6,
            max_k_for_mld=16,
        ),
        results_dir=results_dir,
        channel_type=channel_type,
        channel_params=dict(channel_params or {}),
    )


NEW_CHANNELS_RAYLEIGH_CONFIG = _new_channels_config(
    "rayleigh", "research_results/channel_comparison/rayleigh"
)
NEW_CHANNELS_SINUSOIDAL_CONFIG = _new_channels_config(
    "sinusoidal",
    "research_results/channel_comparison/sinusoidal",
    NEW_CHANNELS_SINUSOIDAL_PARAMS,
)
NEW_CHANNELS_RAYLEIGH_AWGN_CONFIG = _new_channels_config(
    "rayleigh_awgn", "research_results/channel_comparison/rayleigh_awgn"
)
NEW_CHANNELS_AWGN_BASELINE_CONFIG = _new_channels_config(
    "awgn", "research_results/channel_comparison/awgn_baseline"
)

# Единый пресет "new_channels_comparison": 5 семейств x 3 новых канала
# x SNR 0..5 dB (AWGN — опциональный baseline).
NEW_CHANNELS_COMPARISON = {
    "rayleigh": NEW_CHANNELS_RAYLEIGH_CONFIG,
    "sinusoidal": NEW_CHANNELS_SINUSOIDAL_CONFIG,
    "rayleigh_awgn": NEW_CHANNELS_RAYLEIGH_AWGN_CONFIG,
}


# Реалистичная синусоидальная интерференция: N случайных тонов,
# случайные амплитуда/частота/фаза + медленный дрейф.
REALISTIC_SINUSOIDAL_TEST_PARAMS = {
    "mode": "realistic",
    "num_interferers": 3,
    "amplitude_distribution": "uniform",
    "amplitude_range": [0.1, 0.5],
    "frequency_range": [0.01, 0.5],
    "drift": True,
    "drift_amplitude_step": 0.002,
    "drift_frequency_step": 0.00015,
    "drift_phase_step": 0.004,
}

REALISTIC_SINUSOIDAL_TEST_CONFIG = ResearchConfig(
    message_count=NEW_CHANNELS_MESSAGE_COUNT,
    message_seed=12345,
    noise_seed=54321,
    ebn0_db_values=NEW_CHANNELS_SNR_DB,
    codes=_load_preset("FIVE_FAMILIES_20K_32_16").codes,  # type: ignore[union-attr]
    decoders=DecoderResearchConfig(
        run_syndrome=True,
        run_hard_mld=True,
        run_soft_mld=True,
        run_chase=True,
        syndrome_max_error_weight=2,
        chase_inner_decoder_max_error_weight=2,
        chase_unreliable_positions_count=6,
        max_k_for_mld=16,
    ),
    results_dir="research_results/channel_comparison/realistic_sinusoidal",
    channel_type="sinusoidal",
    channel_params=dict(REALISTIC_SINUSOIDAL_TEST_PARAMS),
)
