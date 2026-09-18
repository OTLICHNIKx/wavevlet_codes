import numpy as np
import pytest
from dataclasses import replace

from research.config import (
    FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
    LDPC_32_16_FIVE_FAMILY_CONFIG,
    NEW_CHANNELS_AWGN_BASELINE_CONFIG,
    NEW_CHANNELS_COMPARISON,
    NEW_CHANNELS_RAYLEIGH_CONFIG,
    NEW_CHANNELS_SINUSOIDAL_CONFIG,
    ResearchConfig,
)
from research.runner import run_research


def _ldpc_base_config():
    return replace(
        FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
        codes=(LDPC_32_16_FIVE_FAMILY_CONFIG,),
        message_count=4,
        ebn0_db_values=(3.0,),
        results_dir="",
    )


def test_research_config_defaults_to_awgn():
    config = _ldpc_base_config()
    assert config.channel_type == "awgn"
    assert config.channel_params == {}


def test_research_config_rejects_unknown_channel():
    with pytest.raises(ValueError, match="Неизвестный канал"):
        replace(_ldpc_base_config(), channel_type="quantum")


def test_research_config_json_roundtrip_keeps_channel():
    config = replace(
        _ldpc_base_config(),
        channel_type="sinusoidal",
        channel_params={"amplitude": 0.7},
    )
    restored = ResearchConfig.from_json_dict(config.to_json_dict())
    assert restored.channel_type == "sinusoidal"
    assert restored.channel_params == {"amplitude": 0.7}


def test_research_config_from_legacy_json_without_channel_fields():
    payload = _ldpc_base_config().to_json_dict()
    del payload["channel_type"]
    del payload["channel_params"]
    restored = ResearchConfig.from_json_dict(payload)
    assert restored.channel_type == "awgn"


def test_awgn_path_reproduces_previous_results(tmp_path):
    # awgn по умолчанию и явный awgn дают идентичные строки
    default_rows = run_research(
        replace(_ldpc_base_config(), results_dir=str(tmp_path / "a"))
    )
    explicit_rows = run_research(
        replace(
            _ldpc_base_config(),
            channel_type="awgn",
            results_dir=str(tmp_path / "b"),
        )
    )
    assert [r["ber"] for r in default_rows] == [r["ber"] for r in explicit_rows]


@pytest.mark.parametrize(
    "channel_type", ["rayleigh", "sinusoidal", "rayleigh_awgn"]
)
def test_new_channels_run_through_full_pipeline(tmp_path, channel_type):
    rows = run_research(
        replace(
            _ldpc_base_config(),
            channel_type=channel_type,
            results_dir=str(tmp_path / channel_type),
        )
    )
    assert rows
    decoders = {row["decoder"] for row in rows if not row["skipped"]}
    assert {"syndrome", "chase", "soft_mld"} <= decoders
    for row in rows:
        if not row["skipped"]:
            assert 0.0 <= row["ber"] <= 1.0


def test_new_channel_results_are_deterministic(tmp_path):
    first = run_research(
        replace(
            _ldpc_base_config(),
            channel_type="rayleigh",
            results_dir=str(tmp_path / "1"),
        )
    )
    second = run_research(
        replace(
            _ldpc_base_config(),
            channel_type="rayleigh",
            results_dir=str(tmp_path / "2"),
        )
    )
    assert [r["ber"] for r in first] == [r["ber"] for r in second]


def test_new_channels_comparison_preset_design():
    assert set(NEW_CHANNELS_COMPARISON) == {
        "rayleigh", "sinusoidal", "rayleigh_awgn",
    }
    assert NEW_CHANNELS_AWGN_BASELINE_CONFIG.channel_type == "awgn"
    for channel_type, config in NEW_CHANNELS_COMPARISON.items():
        assert config.channel_type == channel_type
        assert config.message_count == 100
        assert config.ebn0_db_values == (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
        assert len(config.codes) == 5
        assert {c.family for c in config.codes} == {
            "wavelet", "bch_derived", "goppa_derived",
            "reed_solomon_binary", "ldpc",
        }
        assert config.results_dir.startswith(
            "research_results/channel_comparison"
        )
    assert NEW_CHANNELS_SINUSOIDAL_CONFIG.channel_params == {
        "amplitude": 0.5, "frequency": 0.125, "phase": 0.0,
    }


def test_channel_seed_shared_between_same_shape_codes(tmp_path):
    # common random numbers: два кода одной формы видят один и тот же fade
    from research.config import (
        WAVELET_16_8_CONFIG,
        LDPC_16_8_CONFIG,
        DecoderResearchConfig,
    )

    config = ResearchConfig(
        message_count=8,
        message_seed=5,
        noise_seed=9,
        ebn0_db_values=(2.0,),
        codes=(
            replace(WAVELET_16_8_CONFIG, name="w_a"),
            replace(WAVELET_16_8_CONFIG, name="w_b", syndrome_max_error_weight=2),
        ),
        decoders=DecoderResearchConfig(
            run_syndrome=True, run_hard_mld=False, run_soft_mld=False,
            run_chase=False,
        ),
        results_dir=str(tmp_path / "crn"),
        channel_type="rayleigh",
    )
    rows = run_research(config)
    ber = {row["code_name"]: row["ber"] for row in rows}
    assert ber["w_a"] == ber["w_b"]


def test_realistic_sinusoidal_preset_design():
    from research.config import REALISTIC_SINUSOIDAL_TEST_CONFIG

    config = REALISTIC_SINUSOIDAL_TEST_CONFIG
    assert config.channel_type == "sinusoidal"
    assert config.channel_params["mode"] == "realistic"
    assert config.channel_params["num_interferers"] == 3
    assert config.message_count == 100
    assert config.ebn0_db_values == (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
    assert {c.family for c in config.codes} == {
        "wavelet", "bch_derived", "goppa_derived",
        "reed_solomon_binary", "ldpc",
    }
    decoders = config.decoders
    assert decoders.run_syndrome and decoders.run_chase
    assert decoders.run_hard_mld and decoders.run_soft_mld


def test_realistic_sinusoidal_experiment_runs_all_four_decoders(tmp_path):
    from research.config import REALISTIC_SINUSOIDAL_TEST_CONFIG

    tiny = replace(
        REALISTIC_SINUSOIDAL_TEST_CONFIG,
        codes=tuple(
            c for c in REALISTIC_SINUSOIDAL_TEST_CONFIG.codes
            if c.family == "ldpc"
        ),
        message_count=4,
        ebn0_db_values=(5.0,),
        results_dir=str(tmp_path / "realistic"),
    )
    rows = run_research(tiny)
    executed = [row for row in rows if not row["skipped"]]
    assert {row["decoder"] for row in executed} == {
        "syndrome", "chase", "hard_mld", "soft_mld",
    }
    # статистика разделена по decoder: разные декодеры дают разные BER
    assert len({row["ber"] for row in executed}) >= 2


def test_realistic_channel_seed_dependent_and_reproducible(tmp_path):
    from research.config import REALISTIC_SINUSOIDAL_TEST_CONFIG

    def ber_a(seed: int):
        rows = run_research(replace(
            REALISTIC_SINUSOIDAL_TEST_CONFIG,
            codes=tuple(
                c for c in REALISTIC_SINUSOIDAL_TEST_CONFIG.codes
                if c.family == "ldpc"
            ),
            message_count=4,
            noise_seed=seed,
            ebn0_db_values=(3.0,),
            results_dir=str(tmp_path / f"r_{seed}"),
        ))
        return [row["ber"] for row in rows if row["decoder"] == "syndrome"]

    assert ber_a(54321) == ber_a(54321)
    assert ber_a(54321) != ber_a(99991)
