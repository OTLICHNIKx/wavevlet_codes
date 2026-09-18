import numpy as np
import pytest

from channel import (
    CHANNEL_TYPES,
    apply_channel,
    rayleigh_awgn_channel,
    rayleigh_channel,
    realized_sinusoidal_parameters,
    sinusoidal_channel,
)


def _block(message_count: int = 4, n: int = 16) -> tuple[np.ndarray, np.ndarray]:
    symbols = 1.0 - 2.0 * np.tile(
        np.arange(message_count * n, dtype=np.uint8).reshape(message_count, n) % 2,
        (1, 1),
    ).astype(float)
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(symbols.shape)
    return symbols, noise


def test_channel_types_complete():
    assert CHANNEL_TYPES == ("awgn", "rayleigh", "sinusoidal", "rayleigh_awgn")


def test_all_channels_preserve_shape_and_run():
    symbols, noise = _block()
    for channel_type in CHANNEL_TYPES:
        received = apply_channel(channel_type, symbols, noise, 1.0, noise_seed=11)
        assert received.shape == symbols.shape
        assert np.all(np.isfinite(received))


def test_awgn_channel_matches_legacy_formula_exactly():
    symbols, noise = _block()
    sigma = 0.63
    received = apply_channel("awgn", symbols, noise, sigma)
    assert np.array_equal(received, symbols + sigma * noise)


def test_rayleigh_seed_reproducibility_and_difference():
    symbols, noise = _block()
    first = apply_channel("rayleigh", symbols, noise, 0.5, noise_seed=42)
    second = apply_channel("rayleigh", symbols, noise, 0.5, noise_seed=42)
    other = apply_channel("rayleigh", symbols, noise, 0.5, noise_seed=43)
    assert np.array_equal(first, second)
    assert not np.allclose(first, other)


def test_rayleigh_blockwise_is_constant_per_row():
    symbols, noise = _block(message_count=3, n=8)
    received = rayleigh_channel(symbols, noise, seed=7)
    h = (received - noise) / symbols
    for row in range(h.shape[0]):
        assert np.allclose(h[row, 0], h[row])


def test_rayleigh_awgn_varies_per_symbol():
    symbols, noise = _block(message_count=1, n=64)
    received = rayleigh_awgn_channel(symbols, noise, seed=7)
    h = (received - noise) / symbols
    assert h.size > 1
    assert float(np.ptp(h)) > 1e-6


def test_rayleigh_fading_unit_average_power():
    rng = np.random.default_rng(5)
    symbols = np.ones((2000, 1))
    noise = np.zeros_like(symbols)
    h_eff = rayleigh_awgn_channel(symbols, noise, seed=99).ravel()
    assert 0.8 < float(np.mean(h_eff * h_eff)) < 1.25


def test_sinusoidal_formula_exact():
    symbols = np.ones((2, 64), dtype=float)
    noise = np.zeros_like(symbols)
    amplitude, frequency, phase = 0.4, 0.125, 0.3
    received = sinusoidal_channel(
        symbols, noise,
        amplitude=amplitude, frequency=frequency, phase=phase,
    )
    t = np.arange(128).reshape(2, 64)
    expected = symbols + amplitude * np.sin(2 * np.pi * frequency * t + phase)
    assert np.allclose(received, expected)


def test_sinusoidal_rejects_bad_frequency():
    symbols = np.ones((1, 8))
    with pytest.raises(ValueError):
        sinusoidal_channel(symbols, symbols, frequency=0.0)
    with pytest.raises(ValueError):
        sinusoidal_channel(symbols, symbols, frequency=0.8)


def test_unknown_channel_rejected():
    symbols, noise = _block()
    with pytest.raises(ValueError):
        apply_channel("quantum", symbols, noise, 0.5)


def test_shape_mismatch_rejected():
    symbols, _noise = _block()
    with pytest.raises(ValueError):
        apply_channel("rayleigh", symbols, symbols[:, :8], 0.5, noise_seed=1)


# ------------------------------------------------------------------
# realistic-режим: несколько случайных тона + дрейф
# ------------------------------------------------------------------

def test_fixed_mode_still_matches_legacy_exact_formula():
    symbols = np.ones((2, 64), dtype=float)
    noise = np.zeros_like(symbols)
    received = sinusoidal_channel(
        symbols, noise, amplitude=0.4, frequency=0.125, phase=0.3
    )
    t = np.arange(128).reshape(2, 64)
    expected = symbols + 0.4 * np.sin(2 * np.pi * 0.125 * t + 0.3)
    assert np.allclose(received, expected)


def test_realistic_seed_reproducibility():
    symbols, noise = _block(message_count=3, n=32)
    kwargs = dict(
        mode="realistic", num_interferers=3, drift=True,
        amplitude_range=(0.1, 0.5), frequency_range=(0.01, 0.5),
    )
    a = sinusoidal_channel(symbols, noise, seed=42, **kwargs)
    b = sinusoidal_channel(symbols, noise, seed=42, **kwargs)
    c = sinusoidal_channel(symbols, noise, seed=43, **kwargs)
    assert np.array_equal(a, b)
    assert not np.allclose(a, c)


def test_realistic_sums_multiple_interferers_with_drift_off():
    symbols = np.ones((1, 200), dtype=float)
    noise = np.zeros_like(symbols)
    received = sinusoidal_channel(
        symbols, noise, mode="realistic", num_interferers=4,
        amplitude_range=(0.2, 0.2), frequency_range=(0.1, 0.4),
        drift=False, seed=11,
    )
    realized = realized_sinusoidal_parameters(
        11, num_interferers=4, amplitude_range=(0.2, 0.2),
        frequency_range=(0.1, 0.4),
    )
    assert len(realized["amplitudes"]) == 4
    t = np.arange(200, dtype=float)
    interference = np.zeros(200)
    for amp, freq, phase in zip(
        realized["amplitudes"], realized["frequencies"], realized["phases"]
    ):
        assert 0.1 <= freq <= 0.4
        assert 0.0 <= phase < 2 * np.pi
        interference += amp * np.sin(2 * np.pi * freq * t + phase)
    assert np.allclose(received[0], symbols[0] + interference)


def test_realistic_gaussian_noise_component_present():
    symbols = np.zeros((10, 100), dtype=float)
    received = sinusoidal_channel(
        symbols, mode="realistic", num_interferers=1,
        amplitude_range=(0.0, 0.0), drift=False,
        gaussian_noise_std=0.5, seed=5,
    )
    residual = received.ravel()
    assert 0.3 < float(np.std(residual)) < 0.7


def test_realistic_rejects_bad_ranges():
    symbols = np.ones((1, 32), dtype=float)
    with pytest.raises(ValueError):
        realized_sinusoidal_parameters(1, frequency_range=(0.0, 0.5))
    with pytest.raises(ValueError):
        realized_sinusoidal_parameters(1, frequency_range=(0.1, 0.9))
    with pytest.raises(ValueError):
        sinusoidal_channel(
            symbols, np.zeros_like(symbols), mode="realistic",
            num_interferers=0, seed=1,
        )


def test_apply_channel_routes_realistic_mode():
    symbols, noise = _block(message_count=2, n=32)
    received = apply_channel(
        "sinusoidal", symbols, noise, 0.4, noise_seed=17,
        channel_params={"mode": "realistic", "num_interferers": 2},
    )
    assert received.shape == symbols.shape
    assert not np.allclose(received, symbols)
