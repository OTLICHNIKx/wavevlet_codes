"""Репортер не должен смешивать быстрые 1K-прогоны с основными 20K.

1K-пресеты пишут результаты в каталоги ``<size>_1k`` внутри того же
корня ``research_results/five_families_channels``, который репортер
обходит rglob'ом. Если фильтр по размеру выборки исчезнет, отчёт
станет сравнивать 1000 и 20000 слов как будто это одно и то же.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from reporter.loader import load_bulk_directory


def _make_summary(path: Path) -> None:
    """Минимальный summary.csv, который loader обязан принять."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "code_name,code_family,decoder,ebn0_db,ber,fer\n"
        "wavelet_16_8,wavelet,syndrome,2.0,0.01,0.05\n"
        "ldpc_16_8,ldpc,syndrome,2.0,0.02,0.08\n",
        encoding="utf-8",
    )


def test_loader_skips_1k_directories(tmp_path: Path) -> None:
    root = tmp_path / "five_families_channels"

    _make_summary(root / "awgn" / "16_8_20k" / "summary.csv")
    _make_summary(root / "awgn" / "32_16_20k" / "summary.csv")
    _make_summary(root / "rayleigh" / "16_8_20k" / "summary.csv")
    # быстрые прогоны в тех же каналах
    _make_summary(root / "awgn" / "16_8_1k" / "summary.csv")
    _make_summary(root / "awgn" / "32_16_1k" / "summary.csv")
    _make_summary(root / "rayleigh" / "16_8_1k" / "summary.csv")

    results, files, _warnings = load_bulk_directory(root)

    names = sorted(Path(f).relative_to(root).as_posix() for f in files)
    assert names == [
        "awgn/16_8_20k/summary.csv",
        "awgn/32_16_20k/summary.csv",
        "rayleigh/16_8_20k/summary.csv",
    ], names
    # строки только из 20K-файлов: 3 файла x 2 строки
    assert len(results) == 6, len(results)


def test_loader_keeps_20k_when_no_1k(tmp_path: Path) -> None:
    root = tmp_path / "five_families_channels"
    _make_summary(root / "awgn" / "16_8_20k" / "summary.csv")

    results, files, warnings = load_bulk_directory(root)

    assert len(files) == 1
    assert len(results) == 2
    assert warnings == []


def test_loader_still_skips_scratch(tmp_path: Path) -> None:
    root = tmp_path / "five_families_channels"
    _make_summary(root / "awgn" / "_scratch" / "16_8_20k" / "summary.csv")
    _make_summary(root / "awgn" / "16_8_20k" / "summary.csv")

    _results, files, _warnings = load_bulk_directory(root)

    names = sorted(Path(f).relative_to(root).as_posix() for f in files)
    assert names == ["awgn/16_8_20k/summary.csv"]


@pytest.mark.parametrize("suffix", ["_1k"])
def test_only_1k_directory_yields_nothing(tmp_path: Path, suffix: str) -> None:
    root = tmp_path / "five_families_channels"
    _make_summary(root / "awgn" / f"16_8{suffix}" / "summary.csv")

    results, files, warnings = load_bulk_directory(root)

    assert files == []
    assert results == []
    assert warnings, "должно быть предупреждение, что файлов не найдено"
