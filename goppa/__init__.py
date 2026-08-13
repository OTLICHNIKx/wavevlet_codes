"""Бинарные Goppa-коды и Goppa-derived подкоды.

Модуль использует переиспользование математики:
    - GF(2^m) из bch/field.py
    - полиномы над GF(2) из bch/polynomial.py
    - GF(2) матрицы/rank из bch/matrices.py

Основная идея:
    1. Строим parent Goppa code Γ(L, g) над GF(2^m).
    2. Если parent dimension K > target_k, строим Goppa-derived подкод
       размерности target_k детерминированным способом (RREF + первые k строк).
    3. Декодирование использует существующие generic-декодеры проекта
       (syndrome, Chase, MLD) — Patterson decoder НЕ реализуется.
"""

from .code import GoppaCode
from .derived import GoppaDerivedCode
from .construction import (
    GoppaConstruction,
    build_goppa_construction,
)

__all__ = [
    "GoppaCode",
    "GoppaDerivedCode",
    "GoppaConstruction",
    "build_goppa_construction",
]
