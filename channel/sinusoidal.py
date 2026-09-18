"""Модели синусоидальной помехи.

Два режима (параметр ``mode``):

* ``fixed`` — историческая детерминированная модель (побайтово
  сохранена): ``received = signal + A*sin(2*pi*f*t + phase) + noise``;
* ``realistic`` — многокомпонентная случайная интерференция:

      received = signal + interference(t) + gaussian_noise
      interference(t) = sum_k Ak(t) * sin(2*pi*fk(t)*t + phase_k)

  где число источников ``num_interferers``, амплитуды и частоты —
  случайные величины из настраиваемых распределений, фазы
  ``phase_k ~ U[0, 2*pi)``, опционален медленный дрейф параметров во
  времени (нестабильный передатчик / промышленная помеха / соседний
  канал). Все draws зависят только от ``seed`` (воспроизводимость).
"""

from __future__ import annotations

from typing import Any

import numpy as np

TWO_PI = 2.0 * np.pi


def _validate_frequency_bounds(frequency_min: float, frequency_max: float) -> None:
    if not 0.0 < frequency_min <= frequency_max <= 0.5:
        raise ValueError(
            "frequency_range должен лежать в (0, 0.5] циклов на символ "
            f"и удовлетворять f_min <= f_max, получено "
            f"({frequency_min}, {frequency_max})"
        )


def realized_sinusoidal_parameters(
    seed: int,
    *,
    num_interferers: int = 3,
    amplitude_distribution: str = "uniform",
    amplitude_range: tuple[float, float] = (0.1, 0.5),
    amplitude_mu: float = 0.3,
    amplitude_sigma: float = 0.1,
    frequency_range: tuple[float, float] = (0.01, 0.5),
) -> dict[str, Any]:
    """
    РеализованныеRandom-параметры интерференции для given seed.

    Детерминированно воссоздаёт то же самое, что использует канал:
    порядок draws — амплитуды, частоты, фазы (по num_interferers).
    """
    if int(num_interferers) < 1:
        raise ValueError("num_interferers должен быть >= 1")
    frequency_min, frequency_max = (float(frequency_range[0]),
                                     float(frequency_range[1]))
    _validate_frequency_bounds(frequency_min, frequency_max)
    rng = np.random.default_rng(seed)
    count = int(num_interferers)
    if amplitude_distribution == "uniform":
        low, high = float(amplitude_range[0]), float(amplitude_range[1])
        if not 0.0 <= low <= high:
            raise ValueError("amplitude_range должен удовлетворять 0 <= min <= max")
        amplitudes = rng.uniform(low, high, size=count)
    elif amplitude_distribution == "normal":
        amplitudes = np.maximum(
            0.0,
            rng.normal(float(amplitude_mu), float(amplitude_sigma), size=count),
        )
    else:
        raise ValueError(
            "amplitude_distribution: uniform или normal, "
            f"получено {amplitude_distribution!r}"
        )
    frequencies = rng.uniform(frequency_min, frequency_max, size=count)
    phases = rng.uniform(0.0, TWO_PI, size=count)
    return {
        "mode": "realistic",
        "num_interferers": count,
        "amplitude_distribution": amplitude_distribution,
        "amplitudes": [float(v) for v in amplitudes],
        "frequencies": [float(v) for v in frequencies],
        "phases": [float(v) for v in phases],
    }


def _drift_walk(
    rng: np.random.Generator,
    start: float,
    step: float,
    size: int,
    low: float,
    high: float,
) -> np.ndarray:
    """Медленный случайный дрейф параметра (рандом-вок с клиппингом)."""
    if step <= 0:
        return np.full(size, float(start))
    walk = float(start) + np.cumsum(
        np.concatenate(([0.0], rng.normal(0.0, step, size=size - 1)))
    ) if size > 1 else np.array([float(start)])
    return np.clip(walk, low, high)


def sinusoidal_channel(
    symbols: np.ndarray,
    noise: np.ndarray | None = None,
    *,
    mode: str = "fixed",
    seed: int = 0,
    amplitude: float = 0.5,
    frequency: float = 0.125,
    phase: float = 0.0,
    num_interferers: int = 3,
    amplitude_distribution: str = "uniform",
    amplitude_range: tuple[float, float] = (0.1, 0.5),
    amplitude_mu: float = 0.3,
    amplitude_sigma: float = 0.1,
    frequency_range: tuple[float, float] = (0.01, 0.5),
    drift: bool = True,
    drift_amplitude_step: float = 0.002,
    drift_frequency_step: float = 0.00015,
    drift_phase_step: float = 0.004,
    snr_db: float | None = None,
    gaussian_noise_std: float | None = None,
) -> np.ndarray:
    """
    Синусоидальный канал.

    fixed-режим ( backward совместим ):
        received = signal + A*sin(2*pi*f*t + phase) + noise
    realistic-режим:
        received = signal + sum_k Ak(t)*sin(2*pi*fk(t)*t + phase_k) + noise

    ``noise`` — заранее масштабированный гауссов шум (пайплайн всегда
    передаёт sigma*base_noise, gaussian noise std управляется SNR);
    для прямого вызова без ``noise`` можно задать ``gaussian_noise_std``
    или ``snr_db`` (BPSK: sigma = sqrt(1/(2*10^(snr/10)))).
    """
    symbols = np.asarray(symbols, dtype=float)
    if mode not in ("fixed", "realistic"):
        raise ValueError(f"mode должен быть fixed или realistic, получено {mode!r}")

    if noise is None:
        if gaussian_noise_std is not None:
            std = float(gaussian_noise_std)
        elif snr_db is not None:
            std = float(np.sqrt(1.0 / (2.0 * 10.0 ** (float(snr_db) / 10.0))))
        else:
            raise ValueError(
                "Нужно передать noise либо gaussian_noise_std либо snr_db"
            )
        rng_noise = np.random.default_rng(seed + 987_654_321)
        noise = rng_noise.normal(0.0, std, size=symbols.shape)
    else:
        noise = np.asarray(noise, dtype=float)
    if symbols.shape != noise.shape:
        raise ValueError("symbols и noise должны иметь одинаковую форму")
    if mode == "fixed":
        if not 0.0 < frequency <= 0.5:
            raise ValueError("frequency должна лежать в (0, 0.5] циклов на символ")
        if amplitude < 0:
            raise ValueError("amplitude должен быть неотрицательным")
        flat_index = np.arange(symbols.size, dtype=float)
        interference = (
            amplitude * np.sin(TWO_PI * frequency * flat_index + phase)
        ).reshape(symbols.shape)
        return symbols + interference + noise

    realized = realized_sinusoidal_parameters(
        seed,
        num_interferers=num_interferers,
        amplitude_distribution=amplitude_distribution,
        amplitude_range=amplitude_range,
        amplitude_mu=amplitude_mu,
        amplitude_sigma=amplitude_sigma,
        frequency_range=frequency_range,
    )
    total_symbols = symbols.size
    rng = np.random.default_rng(seed + 123_456_789)
    interference = np.zeros(total_symbols, dtype=float)
    for amplitude_k, frequency_k, phase_k in zip(
        realized["amplitudes"],
        realized["frequencies"],
        realized["phases"],
    ):
        if drift:
            amplitudes_t = _drift_walk(
                rng, amplitude_k, drift_amplitude_step,
                total_symbols, 0.0, 2.0,
            )
            frequencies_t = _drift_walk(
                rng, frequency_k, drift_frequency_step,
                total_symbols, 0.0, 0.5,
            )
            phase_noise = np.concatenate((
                [0.0],
                np.cumsum(
                    rng.normal(0.0, drift_phase_step, size=total_symbols - 1)
                ),
            )) if total_symbols > 1 else np.zeros(1)
            # Накопленная фаза: theta(t) = phase_k + sum_{u<=t} 2*pi*f(u)
            # + медленный фазовый шум.
            theta = phase_k + np.cumsum(TWO_PI * frequencies_t) + phase_noise
            interference += amplitudes_t * np.sin(theta)
        else:
            t = np.arange(total_symbols, dtype=float)
            interference += amplitude_k * np.sin(
                TWO_PI * frequency_k * t + phase_k
            )
    return symbols + interference.reshape(symbols.shape) + noise


__all__ = [
    "realized_sinusoidal_parameters",
    "sinusoidal_channel",
]
