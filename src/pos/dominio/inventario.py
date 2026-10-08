"""Control de existencias (stock)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .errores import ReglaInventarioInvalida


class MotivoAjuste(str, Enum):
    """Motivos válidos para un ajuste de inventario."""

    MERMA = "merma"
    ROBO = "robo"
    VENCIMIENTO = "vencimiento"
    INVENTARIO_FISICO = "inventario_fisico"
    INGRESO_MANUAL = "ingreso_manual"


@dataclass(frozen=True)
class AjusteInventario:
    """Registro inmutable de un ajuste de inventario (diferencia de conteo, merma, robo, etc.)."""

    codigo_producto: str
    cantidad_anterior: Decimal
    cantidad_nueva: Decimal
    motivo: MotivoAjuste
    usuario: str
    fecha: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cantidad_anterior", Decimal(str(self.cantidad_anterior)))
        object.__setattr__(self, "cantidad_nueva", Decimal(str(self.cantidad_nueva)))

    @property
    def diferencia_conteo(self) -> Decimal:
        """Diferencia entre la cantidad nueva contada y la cantidad anterior."""
        return self.cantidad_nueva - self.cantidad_anterior


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
