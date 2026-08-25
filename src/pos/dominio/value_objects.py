"""Objetos de valor del dominio (inmutables, comparables por valor)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .errores import DatosProductoInvalidos


def _a_pesos(valor: Decimal) -> int:
    """Redondea un Decimal a pesos enteros con politica HALF_UP.

    Politica de redondeo del negocio: medio hacia arriba (0.5 -> 1). Es la mas
    intuitiva para precios de cara al cliente y se fija de forma explicita para no
    depender del redondeo por defecto de Decimal (medio-par).
    """
    return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Dinero:
    """Monto en pesos chilenos (CLP), sin decimales por convencion del negocio.

    Se modela como value object para evitar pasar `int`/`float` sueltos y para
    concentrar la validacion (no se permiten montos negativos). El redondeo a peso
    entero usa politica HALF_UP explicita (ver `_a_pesos`).
    """

    monto: int
    moneda: str = "CLP"

    def __post_init__(self) -> None:
        if not isinstance(self.monto, int):
            raise DatosProductoInvalidos("El monto debe ser entero (CLP sin decimales)")
        if self.monto < 0:
            raise DatosProductoInvalidos("El monto no puede ser negativo")

    @classmethod
    def desde_decimal(cls, valor: Decimal, moneda: str = "CLP") -> Dinero:
        return cls(_a_pesos(valor), moneda)

    def __add__(self, otro: Dinero) -> Dinero:
        self._misma_moneda(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def multiplicado_por(self, factor: Decimal) -> Dinero:
        return Dinero(_a_pesos(Decimal(self.monto) * factor), self.moneda)

    def _misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise DatosProductoInvalidos("No se pueden operar montos de distinta moneda")
