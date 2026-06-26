from dataclasses import dataclass


@dataclass(frozen=True)
class CodeResearchConfig:
    """
    Настройки одного исследуемого кода.
    """

    name: str
    n: int
    k: int
    h: tuple[int, ...]
    a: int = 1
    b: int = 1
    shift: int = 1


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
    # Для k=32 полный перебор практически невозможен.
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


DEFAULT_RESEARCH_CONFIG = ResearchConfig(
    message_count=10_000,

    # Отдельные seed для сообщений и шума.
    # Так проще воспроизводить эксперимент.
    message_seed=12345,
    noise_seed=54321,

    # Диапазон Eb/N0 в дБ.
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
        CodeResearchConfig(
            name="wavelet_16_8",
            n=16,
            k=8,
            h=(1, 0),
        ),
        CodeResearchConfig(
            name="wavelet_32_16",
            n=32,
            k=16,
            h=(1, 0),
        ),
        CodeResearchConfig(
            name="wavelet_64_32",
            n=64,
            k=32,
            h=(1, 0),
        ),
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