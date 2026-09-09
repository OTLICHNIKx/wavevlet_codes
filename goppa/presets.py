"""Фиксированные пресеты Goppa-derived кодов.

Параметры выбраны детерминированно и сохранены здесь,
чтобы избежать случайного поиска при каждом запуске.

Коэффициенты g(x) принадлежат GF(2^m), поэтому для [16,8]
используется исходная конструкция m=4, deg(g)=2, L=GF(16).
"""

from .construction import GoppaConstruction, build_goppa_construction
from .code import GoppaCode
from .derived import GoppaDerivedCode


# [16,8]: m=4, deg=2, полный support GF(16)
GOPPA_16_8_CONSTRUCTION = build_goppa_construction(
    m=4,
    degree=2,
    seed=42,
)
GOPPA_16_8_PARENT = GoppaCode.from_construction(GOPPA_16_8_CONSTRUCTION)
GOPPA_16_8_CODE = GoppaDerivedCode.from_parent(
    GOPPA_16_8_PARENT,
    target_k=8,
    name="goppa_derived_16_8",
)


# [32,16]: m=5, deg=3, seed=3, primitive_polynomial=59 (GF(2^5)=x^5+x^4+x^3+x^2+1).
# Derived subcode выбран не rref_first_k, а гиперплоскостью ker f в
# пространстве сообщений parent (derivation_method=
# "message_functional_kernel", phase-2 оптимизация:
# research/optimization/phase2/optimize_goppa_phase2.py +
# goppa_phase2_hyperplane.json). Функционал f строго отделяет все 128
# слов веса 7 parent-кода (решение СЛАУ f·w=1 над GF(2)), поэтому
# subcode имеет точный d_min=8 (перебор 2^16, A_8=400).
GOPPA_32_16_CONSTRUCTION = build_goppa_construction(
    m=5,
    degree=3,
    seed=3,
    primitive_polynomial=59,
)
GOPPA_32_16_PARENT = GoppaCode.from_construction(GOPPA_32_16_CONSTRUCTION)
GOPPA_32_16_SUBCODE_FUNCTIONAL = (
    0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1,
)
GOPPA_32_16_CODE = GoppaDerivedCode.from_parent(
    GOPPA_32_16_PARENT,
    target_k=16,
    name="goppa_derived_32_16",
    subcode_functional=GOPPA_32_16_SUBCODE_FUNCTIONAL,
)


# [64,32]: m=6, deg=4
GOPPA_64_32_CONSTRUCTION = build_goppa_construction(
    m=6,
    degree=4,
    seed=42,
)
GOPPA_64_32_PARENT = GoppaCode.from_construction(GOPPA_64_32_CONSTRUCTION)
GOPPA_64_32_CODE = GoppaDerivedCode.from_parent(
    GOPPA_64_32_PARENT,
    target_k=32,
    name="goppa_derived_64_32",
)


__all__ = [
    "GOPPA_16_8_CONSTRUCTION",
    "GOPPA_16_8_PARENT",
    "GOPPA_16_8_CODE",
    "GOPPA_32_16_CONSTRUCTION",
    "GOPPA_32_16_PARENT",
    "GOPPA_32_16_CODE",
    "GOPPA_64_32_CONSTRUCTION",
    "GOPPA_64_32_PARENT",
    "GOPPA_64_32_CODE",
]
