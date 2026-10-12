"""Единые структуры данных модуля reporter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Группы семейств для отчёта (ТЗ сравнивает Wavelet с BCH/Goppa/LDPC/RS).
FAMILY_GROUPS: dict[str, str] = {
    "wavelet": "wavelet",
    "bch": "bch",
    "bch_derived": "bch",
    "goppa": "goppa",
    "goppa_derived": "goppa",
    "reed_solomon": "reed_solomon",
    "reed_solomon_binary": "reed_solomon",
    "ldpc": "ldpc",
}

FAMILY_LABELS: dict[str, str] = {
    "wavelet": "Wavelet",
    "bch": "BCH",
    "goppa": "Goppa",
    "reed_solomon": "Reed-Solomon",
    "ldpc": "LDPC",
}

WAVELET_GROUP = "wavelet"

# Минимальное относительное преимущество BER, чтобы считать победу
# содержательной: gain = BER_other / BER_wavelet >= 1 + MIN_REL_GAIN.
# Различия меньше порога считаются ничьей (статистический шум).
MIN_REL_GAIN = 0.02

# Порог z-score для биномиальной проверки значимости (bulk-прогоны).
SIGNIFICANCE_Z = 2.0


def family_group(code_family: str) -> str:
    """Приводит конкретное семейство к группе отчёта."""
    return FAMILY_GROUPS.get(code_family.strip().lower(), code_family.strip().lower())


@dataclass(frozen=True)
class ExperimentResult:
    """Одна точка результата эксперимента (код x декодер x SNR)."""

    experiment_name: str
    source: str  # "bulk" (большой эксперимент) или "monte_carlo"
    code_family: str
    family_group: str
    code_name: str
    decoder: str
    channel: str
    n: int | None
    k: int | None
    snr: float | None
    ber: float | None
    fer: float | None
    message_count: int | None = None
    skipped: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    # Данные для проверки статистической значимости.
    # total_bits: bulk-прогоны (binomial sigma = sqrt(p(1-p)/total_bits)).
    # ber_ci_low/ber_ci_high: Monte Carlo (95% CI по сидам).
    total_bits: int | None = None
    ber_ci_low: float | None = None
    ber_ci_high: float | None = None

    # Ёмкость декодера этой строки (bulk summary.csv: колонки syndrome_t).
    # None — нет данных (MC-файлы не несут t).
    syndrome_t: int | None = None

    @property
    def is_wavelet(self) -> bool:
        return self.family_group == WAVELET_GROUP

    @property
    def code_size(self) -> str:
        if self.n is None or self.k is None:
            return "unknown"
        return f"{self.n}/{self.k}"


@dataclass(frozen=True)
class ComparisonPoint:
    """Сравнение Wavelet и конкурента в конкретной точке."""

    source: str
    experiment_name: str
    channel: str
    code_size: str
    decoder: str
    snr: float
    competitor: str
    wavelet_ber: float
    competitor_ber: float
    gain: float  # BER_other / BER_wavelet
    win: bool
    # Различие значимо статистически (z-score / непересечение CI)
    # и превышает MIN_REL_GAIN. Незначимая разница = ничья.
    significant: bool = True
    # Компетентный проигрыш: конкурент значимо лучше на ту же норму.
    loss: bool = False
    # Ёмкости декодеров сравниваемой пары (None — неизвестно, MC-старые).
    wavelet_t: int | None = None
    competitor_t: int | None = None
    # 95% CI BER (MC) — если заданы, вердикт строится по непересечению.
    wavelet_ci: tuple[float, float] | None = None
    competitor_ci: tuple[float, float] | None = None

    @property
    def equal_capacity(self) -> bool | None:
        """True — сравнение при равном t; False — t различается; None — неизвестно."""
        if self.wavelet_t is None or self.competitor_t is None:
            return None
        return self.wavelet_t == self.competitor_t


@dataclass
class FamilySummary:
    """Свод по одному конкурирующему семейству."""

    competitor: str
    comparisons: int = 0
    wins: int = 0
    ties: int = 0
    losses: int = 0
    # Разбивка побед по совпадению ёмкости декодера (syndrome t).
    wins_equal_t: int = 0
    wins_unequal_t: int = 0
    wins_unknown_t: int = 0
    mean_gain: float = 0.0
    max_gain: float = 0.0
    median_gain: float = 0.0
    snr_ranges: list[tuple[float, float]] = field(default_factory=list)
    points: list[ComparisonPoint] = field(default_factory=list)


@dataclass
class Zone:
    """Зона доминирования Wavelet по (канал, размер, декодер)."""

    channel: str
    code_size: str
    decoder: str
    snr_start: float
    snr_end: float
    mean_gain: float
    competitors: tuple[str, ...]
    experiments: tuple[str, ...] = ()
    # None — t неизвестен; False — победа при разном t (артефакт ёмкости);
    # True — сравнение при равном t (чистое преимущество кода).
    equal_t: bool | None = None


@dataclass
class CapacityVerdict:
    """Вердикт по точкам равной ёмкости декодера (equal_t=True), MC CI.

    Итог на группе (канал, размер, декодер, конкурент): сколько точек,
    где CI 95% не пересекаются, закончили win/loss/tie.
    """

    channel: str
    code_size: str
    decoder: str
    competitor: str
    total: int = 0
    wavelet_wins: int = 0
    competitor_wins: int = 0
    ties: int = 0
    sources: tuple[str, ...] = ()


@dataclass
class LeaderboardRow:
    """Строка таблицы лидеров."""

    channel: str
    code_size: str
    decoder: str
    snr_range: str
    mean_gain: float
    wins: int
    total: int
    experiments: tuple[str, ...] = ()
    equal_t: bool | None = None

    @property
    def equal_t_label(self) -> str:
        if self.equal_t is None:
            return "?"
        return "равный t" if self.equal_t else "разный t ⚠️"


@dataclass
class LoadedData:
    """Все загруженные результаты."""

    results: list[ExperimentResult] = field(default_factory=list)
    bulk_files: list[str] = field(default_factory=list)
    mc_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def bulk_results(self) -> list[ExperimentResult]:
        return [r for r in self.results if r.source == "bulk"]

    @property
    def mc_results(self) -> list[ExperimentResult]:
        return [r for r in self.results if r.source == "monte_carlo"]


@dataclass
class AnalysisResult:
    """Результат анализа."""

    points: list[ComparisonPoint] = field(default_factory=list)
    family_summaries: dict[str, FamilySummary] = field(default_factory=dict)
    zones: list[Zone] = field(default_factory=list)
    leaderboard: list[LeaderboardRow] = field(default_factory=list)
    loss_points: list[ComparisonPoint] = field(default_factory=list)
    mc_confirmed: list[Zone] = field(default_factory=list)
    mc_unstable: list[Zone] = field(default_factory=list)
    capacity_verdicts: list[CapacityVerdict] = field(default_factory=list)
    conclusions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_points(self) -> int:
        return len(self.points)

    @property
    def win_points(self) -> int:
        return sum(1 for p in self.points if p.win)

    @property
    def loss_points_count(self) -> int:
        return sum(1 for p in self.points if p.loss)

    @property
    def tie_points(self) -> int:
        """Ничьи: ни значимой победы, ни значимого поражения."""
        return sum(1 for p in self.points if not p.win and not p.loss)
