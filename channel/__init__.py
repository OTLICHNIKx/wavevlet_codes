"""Реестр моделей каналов для experimental pipeline.

Существующий AWGN (``apply_awgn_from_base_noise`` в research/dataset.py
и ``awgn_channel`` здесь) не изменён: канал ``awgn`` в реестре — тупо
прокидывает формулу ``signal + noise``. Новые каналы добавляются
функциями вида (symbols, noise, **params) -> received, сохраняющими
форму входа и воспроизводимыми по seed.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from .awgn import awgn_channel
from .rayleigh import (
    rayleigh_awgn_channel,
    rayleigh_channel,
    rayleigh_fading_channel,
)
from .sinusoidal import realized_sinusoidal_parameters, sinusoidal_channel

CHANNEL_TYPES = ("awgn", "rayleigh", "sinusoidal", "rayleigh_awgn")

ChannelModel = Callable[..., np.ndarray]


def _plain_awgn(symbols, noise):
    return np.asarray(symbols, dtype=float) + np.asarray(noise, dtype=float)


REGISTRY: dict[str, ChannelModel] = {
    "awgn": _plain_awgn,
    "rayleigh": rayleigh_channel,
    "sinusoidal": sinusoidal_channel,
    "rayleigh_awgn": rayleigh_awgn_channel,
}

# Параметры по умолчанию для новых каналов (исследовательно
# переопределяются channel_params в ResearchConfig).
# sinusoidal по умолчанию остаётся ИСТОРИЧЕСКИМ fixed-режимом
# (существующие пресеты/результаты воспроизводятся побайтово);
# реалистичный многокомпонентный режим включается mode="realistic".
DEFAULT_CHANNEL_PARAMS: dict[str, dict[str, Any]] = {
    "awgn": {},
    "rayleigh": {},
    "rayleigh_awgn": {},
    "sinusoidal": {
        "mode": "fixed",
        "amplitude": 0.5,
        "frequency": 0.125,
        "phase": 0.0,
        "num_interferers": 3,
        "amplitude_distribution": "uniform",
        "amplitude_range": [0.1, 0.5],
        "frequency_range": [0.01, 0.5],
        "drift": True,
    },
}


def validate_channel_type(channel_type: str) -> str:
    if channel_type not in REGISTRY:
        raise ValueError(
            "Неизвестный канал: {0!r}. Допустимы: {1}".format(
                channel_type, ", ".join(CHANNEL_TYPES)
            )
        )
    return channel_type


def resolve_channel_params(
    channel_type: str, channel_params: dict[str, Any] | None
) -> dict[str, Any]:
    merged = dict(DEFAULT_CHANNEL_PARAMS[validate_channel_type(channel_type)])
    if channel_params:
        merged.update(dict(channel_params))
    return merged


def apply_channel(
    channel_type: str,
    transmitted_symbols: np.ndarray,
    base_noise: np.ndarray,
    sigma: float,
    *,
    noise_seed: int = 0,
    channel_params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    Единая точка входа: (transmitted, base_noise, sigma, seed) -> received.

    gaussian noise = sigma * base_noise (тот же общий шум, что и в
    существующем AWGN-конвейере — common random numbers сохранены);
    seed добавляется к drawing собственных случайных параметров канала
    (релеевских коэффициентов).
    """
    validate_channel_type(channel_type)
    if sigma < 0:
        raise ValueError("sigma не может быть отрицательным")
    transmitted = np.asarray(transmitted_symbols, dtype=float)
    noise = sigma * np.asarray(base_noise, dtype=float)
    if transmitted.shape != noise.shape:
        raise ValueError(
            "transmitted_symbols и base_noise должны иметь одинаковую форму"
        )
    params = resolve_channel_params(channel_type, channel_params)
    if channel_type == "awgn":
        return _plain_awgn(transmitted, noise)
    if channel_type in ("rayleigh", "rayleigh_awgn"):
        return REGISTRY[channel_type](transmitted, noise, **params, seed=noise_seed)
    return REGISTRY[channel_type](transmitted, noise, **params, seed=noise_seed)


__all__ = [
    "CHANNEL_TYPES",
    "DEFAULT_CHANNEL_PARAMS",
    "REGISTRY",
    "awgn_channel",
    "apply_channel",
    "rayleigh_channel",
    "rayleigh_awgn_channel",
    "rayleigh_fading_channel",
    "realized_sinusoidal_parameters",
    "sinusoidal_channel",
    "validate_channel_type",
    "resolve_channel_params",
]
