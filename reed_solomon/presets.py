"""Воспроизводимые пресеты binary-image Generalized Reed--Solomon."""
from .code import ReedSolomonBinaryCode

# Target GRS(4,2) over GF(16): binary [16,8,5].
REED_SOLOMON_16_8_CODE = ReedSolomonBinaryCode.from_parameters(
    m=4,
    symbol_n=4,
    symbol_k=2,
    primitive_polynomial=0b10011,
    evaluation_points=(0, 1, 2, 3),
    column_multipliers=(1, 3, 1, 3),
    name="reed_solomon_binary_16_8",
)

# Fixed GRS constructions over the same GF(16) representation.
REED_SOLOMON_32_16_CODE = ReedSolomonBinaryCode.from_parameters(
    m=4,
    symbol_n=8,
    symbol_k=4,
    primitive_polynomial=0b10011,
    evaluation_points=(0, 1, 2, 3, 4, 5, 6, 7),
    column_multipliers=(1, 1, 1, 1, 1, 1, 1, 1),
    name="reed_solomon_binary_32_16",
)

REED_SOLOMON_64_32_CODE = ReedSolomonBinaryCode.from_parameters(
    m=4,
    symbol_n=16,
    symbol_k=8,
    primitive_polynomial=0b10011,
    evaluation_points=tuple(range(16)),
    column_multipliers=(1,) * 16,
    name="reed_solomon_binary_64_32",
)
