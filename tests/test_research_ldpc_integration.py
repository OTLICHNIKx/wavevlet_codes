import numpy as np
import pytest

from ldpc import LDPCCode
from ldpc.presets import LDPC_16_8, LDPC_32_16, LDPC_64_32
from research.code_factory import build_code_from_config
from research.config import (
    CodeResearchConfig,
    FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
    FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
    FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
    LDPC_16_8_CONFIG,
    LDPC_32_16_CONFIG,
    LDPC_64_32_CONFIG,
)


@pytest.mark.parametrize(
    ("config", "preset"),
    [
        (LDPC_16_8_CONFIG, LDPC_16_8),
        (LDPC_32_16_CONFIG, LDPC_32_16),
        (LDPC_64_32_CONFIG, LDPC_64_32),
    ],
)
def test_factory_returns_frozen_ldpc_preset(config, preset) -> None:
    code = build_code_from_config(config)
    assert isinstance(code, LDPCCode)
    assert code is preset
    assert (code.n, code.k) == (config.n, config.k)
    message = np.arange(config.k, dtype=np.uint8) % 2
    codeword = code.encode(message)
    assert codeword.shape == (config.n,)
    assert code.is_codeword(codeword)


def test_ldpc_config_json_round_trip() -> None:
    restored = CodeResearchConfig.from_json_dict(
        LDPC_16_8_CONFIG.to_json_dict()
    )
    assert restored == LDPC_16_8_CONFIG
    assert restored.family == "ldpc"


def test_ldpc_rejects_unknown_dimensions() -> None:
    with pytest.raises(ValueError, match="ldpc"):
        CodeResearchConfig(
            name="ldpc_20_10",
            family="ldpc",
            n=20,
            k=10,
        )


def test_ldpc_decoder_params_match_four_family_presets_per_size() -> None:
    expected = {
        16: (2, 2, 4),
        32: (2, 2, 6),
        64: (3, 3, 8),
    }
    for config in (
        LDPC_16_8_CONFIG,
        LDPC_32_16_CONFIG,
        LDPC_64_32_CONFIG,
    ):
        t_syndrome, t_chase, p = expected[config.n]
        assert config.syndrome_max_error_weight == t_syndrome
        assert config.chase_inner_decoder_max_error_weight == t_chase
        assert config.chase_unreliable_positions_count == p


@pytest.mark.parametrize(
    "config",
    [
        FIVE_FAMILIES_20K_FULL_DECODERS_16_8,
        FIVE_FAMILIES_20K_FULL_DECODERS_32_16,
        FIVE_FAMILIES_20K_FULL_DECODERS_64_32,
    ],
)
def test_five_family_experiment_adds_ldpc_to_existing_four(config) -> None:
    families = [code.family for code in config.codes]
    assert families[:4] == [
        "wavelet",
        "bch_derived",
        "goppa_derived",
        "reed_solomon_binary",
    ]
    assert families[4] == "ldpc"
    assert config.codes[4].name.endswith("_five_family")
    assert config.message_count == 20_000
    assert config.message_seed == 12345
    assert config.noise_seed == 54321
    assert config.decoders.run_syndrome
    assert config.decoders.run_hard_mld
    assert config.decoders.run_soft_mld
    assert config.decoders.run_chase
    assert config.decoders.max_k_for_mld == 16
