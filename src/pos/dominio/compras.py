"""Facturas de compra a proveedor (HU-CMP-01, HU-CMP-02).

Al confirmar una factura, el costo neto de cada producto se actualiza desde el documento del
proveedor y la mercaderia entra al inventario (con su lote si vence). Los gastos generales del
local (luz, agua, arriendo) quedan fuera a pedido de las propietarias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from .errores import ReglaCompraInvalida
from .value_objects import TASA_IVA, Dinero


class EstadoFactura(StrEnum):
    CONFIRMADA = "confirmada"


def iva_de(neto: int) -> int:
    """19 % del neto, al peso. El impuesto adicional (IABA) se corrige a mano en la pantalla."""
    return int((Decimal(neto) * TASA_IVA).quantize(Decimal("1")))


@dataclass
class LineaFactura:
    codigo_producto: str
    cantidad: Decimal
    costo_unitario_neto: int
    fecha_vencimiento: date | None = None
    codigo_lote: str = ""
    # Se llena al confirmar: costo neto que tenia el producto antes de esta factura.
    costo_anterior: int | None = None

    def __post_init__(self) -> None:
        self.cantidad = Decimal(str(self.cantidad))
        if self.cantidad <= 0:
            raise ReglaCompraInvalida("La cantidad de cada línea debe ser mayor que cero")
        if self.costo_unitario_neto <= 0:
            raise ReglaCompraInvalida("El costo unitario neto debe ser mayor que cero")

    @property
    def subtotal(self) -> int:
        return Dinero(self.costo_unitario_neto).multiplicado_por(self.cantidad).monto


@dataclass
class FacturaCompra:
    proveedor: str
    numero: str
    fecha: date
    neto: int
    impuestos: int
    lineas: list[LineaFactura] = field(default_factory=list)
    estado: EstadoFactura = EstadoFactura.CONFIRMADA
    id: int | None = None

    @property
    def total(self) -> int:
        return self.neto + self.impuestos

    @property
    def suma_detalle(self) -> int:
        return sum(linea.subtotal for linea in self.lineas)

    @property
    def diferencia(self) -> int:
        """Neto declarado menos la suma del detalle: debe ser cero para confirmar."""
        return self.neto - self.suma_detalle

    def validar(self) -> None:
        if not self.proveedor.strip():
            raise ReglaCompraInvalida("Falta el proveedor")
        if not self.numero.strip():
            raise ReglaCompraInvalida("Falta el número de documento")
        if not self.lineas:
            raise ReglaCompraInvalida("La factura no tiene productos: agrega al menos una línea")
        if self.neto <= 0:
            raise ReglaCompraInvalida("El monto neto debe ser mayor que cero")
        if self.impuestos < 0:
            raise ReglaCompraInvalida("Los impuestos no pueden ser negativos")
        if self.diferencia != 0:
            raise ReglaCompraInvalida(
                f"El neto no coincide con la suma del detalle (diferencia de ${self.diferencia}); "
                "debe ser cero para confirmar"
            )


@dataclass(frozen=True)
class Proveedor:
    """Quien nos vende la mercaderia. Basta el nombre; el contacto es opcional (HU-CMP-03)."""

    nombre: str
    contacto: str = ""
    id: int | None = None
