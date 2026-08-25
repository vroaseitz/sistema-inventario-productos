"""Objetos de valor del dominio (inmutables, comparables por valor)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .errores import DatosProductoInvalidos


@dataclass(frozen=True)
class Dinero:
    """Monto en pesos chilenos (CLP), sin decimales por convencion del negocio.

    Se modela como value object para evitar pasar `int`/`float` sueltos y para
    concentrar la validacion (no se permiten montos negativos).
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
        return cls(int(valor.to_integral_value()), moneda)

    def __add__(self, otro: Dinero) -> Dinero:
        self._misma_moneda(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def multiplicado_por(self, factor: Decimal) -> Dinero:
        return Dinero(int((Decimal(self.monto) * factor).to_integral_value()), self.moneda)

    def _misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise DatosProductoInvalidos("No se pueden operar montos de distinta moneda")
