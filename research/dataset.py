from dataclasses import dataclass

import numpy as np

from .config import CodeResearchConfig


@dataclass(frozen=True)
class CodeResearchDataset:
    """
    Набор данных для одного исследуемого кода.

    messages:
        информационные сообщения размера message_count x k

    base_noise:
        базовый нормальный шум N(0, 1) размера message_count x n

    Важно:
        base_noise один и тот же для всех декодеров.
        Для разных Eb/N0 он только масштабируется через sigma.
    """

    code_config: CodeResearchConfig
    messages: np.ndarray
    base_noise: np.ndarray
    message_seed: int
    noise_seed: int


def make_code_seed(
    base_seed: int,
    code_config: CodeResearchConfig,
    salt: int = 0,
) -> int:
    """
    Строит воспроизводимый seed для конкретного кода.

    Не используем hash(), потому что в Python он может быть разным
    между запусками. Здесь формула полностью детерминированная.
    """
    return int(base_seed + salt + 10_000 * code_config.n + code_config.k)


def generate_messages_for_code(
    message_count: int,
    code_config: CodeResearchConfig,
    seed: int,
) -> np.ndarray:
    """
    Генерирует случайные информационные сообщения для конкретного кода.

    Размер:
        message_count x k

    Каждый бит равновероятно равен 0 или 1.
    """
    if message_count <= 0:
        raise ValueError("message_count должно быть положительным")

    if code_config.k <= 0:
        raise ValueError("k должно быть положительным")

    rng = np.random.default_rng(seed)

    return rng.integers(
        low=0,
        high=2,
        size=(message_count, code_config.k),
        dtype=np.uint8,
    )


def generate_noise_for_code(
    message_count: int,
    code_config: CodeResearchConfig,
    seed: int,
) -> np.ndarray:
    """
    Генерирует базовый нормальный шум для конкретного кода.

    Размер:
        message_count x n

    Шум имеет распределение N(0, 1).
    Дальше он масштабируется через sigma.
    """
    if message_count <= 0:
        raise ValueError("message_count должно быть положительным")

    if code_config.n <= 0:
        raise ValueError("n должно быть положительным")

    rng = np.random.default_rng(seed)

    return rng.normal(
        loc=0.0,
        scale=1.0,
        size=(message_count, code_config.n),
    )


def build_dataset_for_code(
    message_count: int,
    code_config: CodeResearchConfig,
    message_seed: int,
    noise_seed: int,
) -> CodeResearchDataset:
    """
    Создаёт полный фиксированный набор данных для одного кода.

    Для каждого кода seed получается из общего seed и параметров кода.
    Поэтому данные:
        1. воспроизводимы;
        2. различаются между кодами;
        3. одинаковы для всех декодеров внутри одного кода.
    """
    code_message_seed = make_code_seed(
        base_seed=message_seed,
        code_config=code_config,
        salt=0,
    )

    code_noise_seed = make_code_seed(
        base_seed=noise_seed,
        code_config=code_config,
        salt=1_000_000,
    )

    messages = generate_messages_for_code(
        message_count=message_count,
        code_config=code_config,
        seed=code_message_seed,
    )

    base_noise = generate_noise_for_code(
        message_count=message_count,
        code_config=code_config,
        seed=code_noise_seed,
    )

    return CodeResearchDataset(
        code_config=code_config,
        messages=messages,
        base_noise=base_noise,
        message_seed=code_message_seed,
        noise_seed=code_noise_seed,
    )


def ebn0_db_to_sigma(
    ebn0_db: float,
    code_rate: float,
) -> float:
    """
    Переводит Eb/N0 в dB в стандартное отклонение шума sigma.

    Для BPSK + AWGN:

        sigma = sqrt(1 / (2 * R * EbN0))

    где:
        R = k / n
        EbN0 = 10^(EbN0_dB / 10)
    """
    if code_rate <= 0:
        raise ValueError("code_rate должен быть положительным")

    ebn0_linear = 10.0 ** (ebn0_db / 10.0)

    sigma = np.sqrt(1.0 / (2.0 * code_rate * ebn0_linear))

    return float(sigma)


def apply_awgn_from_base_noise(
    transmitted_symbols: np.ndarray,
    base_noise: np.ndarray,
    sigma: float,
) -> np.ndarray:
    """
    Добавляет AWGN-шум к переданным BPSK-символам.

    Используется заранее созданный base_noise:

        received = transmitted_symbols + sigma * base_noise

    Поэтому для всех декодеров канал одинаковый.
    """
    transmitted_symbols = np.asarray(transmitted_symbols, dtype=float)
    base_noise = np.asarray(base_noise, dtype=float)

    if transmitted_symbols.shape != base_noise.shape:
        raise ValueError(
            "transmitted_symbols и base_noise должны иметь одинаковую форму"
        )

    if sigma < 0:
        raise ValueError("sigma не может быть отрицательным")

    return transmitted_symbols + sigma * base_noise


def build_all_datasets(
    message_count: int,
    codes: tuple[CodeResearchConfig, ...],
    message_seed: int,
    noise_seed: int,
) -> dict[str, CodeResearchDataset]:
    """
    Создаёт наборы данных для всех исследуемых кодов.
    """
    datasets: dict[str, CodeResearchDataset] = {}

    for code_config in codes:
        dataset = build_dataset_for_code(
            message_count=message_count,
            code_config=code_config,
            message_seed=message_seed,
            noise_seed=noise_seed,
        )

        datasets[code_config.name] = dataset

    return datasets