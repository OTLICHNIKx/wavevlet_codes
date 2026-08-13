import numpy as np
import pytest

from goppa import GoppaDerivedCode
from research.code_factory import build_code_from_config
from research.config import (
    EQUAL_DECODER_20K_THREE_FAMILIES,
    GOPPA_16_8_CONFIG,
    GOPPA_32_16_CONFIG,
    GOPPA_64_32_CONFIG,
)


CONFIGS = (
    (GOPPA_16_8_CONFIG, 16, 8),
    (GOPPA_32_16_CONFIG, 32, 16),
    (GOPPA_64_32_CONFIG, 64, 32),
)


@pytest.mark.parametrize("config,n,k", CONFIGS)
def test_factory_builds_all_goppa_presets(config, n, k) -> None:
    code = build_code_from_config(config)

    assert isinstance(code, GoppaDerivedCode)
    assert (code.n, code.k) == (n, k)
    message = np.random.default_rng(n).integers(0, 2, size=k, dtype=np.uint8)
    assert np.all(code.syndrome(code.encode(message)) == 0)


def test_three_family_20k_preset_uses_equal_parameters() -> None:
    config = EQUAL_DECODER_20K_THREE_FAMILIES

    assert config.message_count == 20_000
    assert config.ebn0_db_values == tuple(value / 2 for value in range(11))
    assert len(config.codes) == 9

    for offset, expected in ((0, (16, 8, 1, 1, 4)),
                             (3, (32, 16, 2, 2, 6)),
                             (6, (64, 32, 3, 3, 8))):
        group = config.codes[offset: offset + 3]
        actual = {
            (
                code.n,
                code.k,
                code.syndrome_max_error_weight,
                code.chase_inner_decoder_max_error_weight,
                code.chase_unreliable_positions_count,
            )
            for code in group
        }
        assert actual == {expected}
