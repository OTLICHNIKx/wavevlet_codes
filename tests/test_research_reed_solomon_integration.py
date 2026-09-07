import numpy as np

from bch import gf2_matrix_rank
from reed_solomon import ReedSolomonBinaryCode
from research.code_factory import build_code_from_config
from research.config import CodeResearchConfig, REED_SOLOMON_16_8_CONFIG


def test_factory_builds_binary_rs_16_8() -> None:
    code = build_code_from_config(REED_SOLOMON_16_8_CONFIG)
    assert isinstance(code, ReedSolomonBinaryCode)
    assert (code.n, code.k) == (16, 8)
    assert code.generator_matrix.shape == (8, 16)
    assert code.parity_check_matrix.shape == (8, 16)
    assert gf2_matrix_rank(code.generator_matrix) == 8
    assert gf2_matrix_rank(code.parity_check_matrix) == 8
    assert np.all(
        (
            code.generator_matrix.astype(np.int64)
            @ code.parity_check_matrix.astype(np.int64).T
        ) % 2 == 0
    )
    message = np.array([1, 0, 0, 1, 1, 0, 1, 0], dtype=np.uint8)
    assert np.array_equal(
        code.encode(message),
        (message.astype(np.int64) @ code.generator_matrix.astype(np.int64) % 2).astype(np.uint8),
    )
    assert code.is_codeword(code.encode(message))


def test_rs_config_json_round_trip_preserves_active_parameters() -> None:
    restored = CodeResearchConfig.from_json_dict(
        REED_SOLOMON_16_8_CONFIG.to_json_dict()
    )
    assert restored == REED_SOLOMON_16_8_CONFIG
    assert restored.family == "reed_solomon_binary"
    assert restored.reed_solomon_m == 4
    assert restored.reed_solomon_symbol_n == 4
    assert restored.reed_solomon_symbol_k == 2
    assert restored.reed_solomon_primitive_polynomial == 0b10011


def test_rs_config_rejects_inconsistent_binary_dimensions() -> None:
    try:
        CodeResearchConfig(
            name="invalid_rs",
            family="reed_solomon_binary",
            n=15,
            k=8,
            reed_solomon_m=4,
            reed_solomon_symbol_n=4,
            reed_solomon_symbol_k=2,
        )
    except ValueError as error:
        assert "n не согласовано" in str(error)
    else:
        raise AssertionError("Inconsistent Reed-Solomon config was accepted")
