"""Control de existencias (stock)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .errores import ReglaInventarioInvalida


@dataclass
class Existencia:
    """Stock de un producto.

    Se usa Decimal para soportar productos a granel (p. ej. 1.250 kg). Para productos
    por unidad, la cantidad sera un entero representado como Decimal.
    """

    codigo_producto: str
    cantidad: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        self.cantidad = Decimal(str(self.cantidad))
        if self.cantidad < 0:
            raise ReglaInventarioInvalida("El stock inicial no puede ser negativo")

    def ingresar(self, cantidad: Decimal) -> None:
        cantidad = Decimal(str(cantidad))
        if cantidad <= 0:
            raise ReglaInventarioInvalida("El ingreso debe ser mayor que cero")
        self.cantidad += cantidad

    def descontar(self, cantidad: Decimal) -> None:
        cantidad = Decimal(str(cantidad))
        if cantidad <= 0:
            raise ReglaInventarioInvalida("El descuento debe ser mayor que cero")
        if cantidad > self.cantidad:
            raise ReglaInventarioInvalida(
                f"Stock insuficiente: hay {self.cantidad}, se piden {cantidad}"
            )
        self.cantidad -= cantidad
