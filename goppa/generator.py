"""Генерация параметров для Goppa-кодов."""

from dataclasses import dataclass

from bch.field import GF2m, create_gf2m

from .construction import GoppaConstruction, build_goppa_construction


@dataclass(frozen=True)
class GoppaParameters:
    """
    Параметры Goppa-кода для воспроизводимости.

    Attributes:
        m: степень расширения GF(2^m)
        degree: степень Goppa polynomial t_goppa
        support_size: размер поддержки |L|
        seed: seed для детерминированного выбора g(x)
        primitive_polynomial: примитивный полином поля (None = default)
    """

    m: int
    degree: int
    support_size: int | None = None
    seed: int = 42
    primitive_polynomial: int | None = None


def build_from_parameters(
    params: GoppaParameters,
) -> GoppaConstruction:
    """Строит конструкцию из параметров."""
    return build_goppa_construction(
        m=params.m,
        degree=params.degree,
        seed=params.seed,
        primitive_polynomial=params.primitive_polynomial,
        support_size=params.support_size,
    )


__all__ = [
    "GoppaParameters",
    "build_from_parameters",
]
