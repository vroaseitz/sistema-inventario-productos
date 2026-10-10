"""Entidad Venta y sus reglas (HU-VTA-01, HU-VTA-03, HU-VTA-04).

La Venta acumula detalles (lineas de producto) y pagos. El total se redondea a la
decena solo si alguno de los pagos es en efectivo (HU-VTA-04): tarjeta y
transferencia conservan el total exacto, sin redondear.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .errores import ReglaVentaInvalida
from .pagos import MedioPago, Pago, redondear_a_decena
from .value_objects import Dinero


class EstadoVenta(Enum):
    """Estado de la venta. La anulacion (HU-VTA-11) queda fuera de este incremento."""

    PAGADA = "pagada"
    ANULADA = "anulada"


@dataclass
class DetalleVenta:
    """Una linea de la venta: un producto, su cantidad y el precio/costo vigentes.

    `costo_unitario` es una instantanea (HU-VTA-01/02): calcular el margen de una
    venta pasada debe usar el costo de ese momento, no el costo actual del producto.
    """

    producto_codigo: str
    cantidad: Decimal
    precio_unitario: Dinero
    costo_unitario: Dinero | None = None
    descuento_linea: Dinero = field(default_factory=lambda: Dinero(0))

    def __post_init__(self) -> None:
        self.cantidad = Decimal(str(self.cantidad))
        if self.cantidad <= 0:
            raise ReglaVentaInvalida("La cantidad de una linea debe ser mayor que cero")

    @property
    def subtotal(self) -> Dinero:
        bruto = self.precio_unitario.multiplicado_por(self.cantidad)
        if self.descuento_linea.monto > bruto.monto:
            raise ReglaVentaInvalida("El descuento de la linea no puede superar su monto bruto")
        return Dinero(bruto.monto - self.descuento_linea.monto)


@dataclass
class Venta:
    turno_caja_id: int
    usuario_id: int
    cliente_id: int | None = None
    detalles: list[DetalleVenta] = field(default_factory=list)
    pagos: list[Pago] = field(default_factory=list)
    estado: EstadoVenta = EstadoVenta.PAGADA
    creado_en: datetime = field(default_factory=datetime.now)

    def agregar_detalle(
        self,
        producto_codigo: str,
        cantidad: Decimal | float,
        precio_unitario: Dinero,
        costo_unitario: Dinero | None = None,
    ) -> DetalleVenta:
        """Agrega una linea; si el producto ya esta en el ticket, suma la cantidad
        en vez de duplicar la linea (HU-VTA-01: leer dos veces el mismo producto)."""
        cantidad_dec = Decimal(str(cantidad))
        for detalle in self.detalles:
            if detalle.producto_codigo == producto_codigo:
                detalle.cantidad += cantidad_dec
                if detalle.cantidad <= 0:
                    raise ReglaVentaInvalida("La cantidad de una linea debe ser mayor que cero")
                return detalle
        detalle = DetalleVenta(
            producto_codigo=producto_codigo,
            cantidad=cantidad_dec,
            precio_unitario=precio_unitario,
            costo_unitario=costo_unitario,
        )
        self.detalles.append(detalle)
        return detalle

    def quitar_detalle(self, producto_codigo: str) -> None:
        """Elimina una linea del ticket antes de cobrar (HU-VTA-01)."""
        for detalle in self.detalles:
            if detalle.producto_codigo == producto_codigo:
                self.detalles.remove(detalle)
                return
        raise ReglaVentaInvalida(f"No hay una linea para el producto {producto_codigo}")

    @property
    def total(self) -> Dinero:
        """Total exacto de la venta, sin redondeo de efectivo."""
        return Dinero(sum((d.subtotal.monto for d in self.detalles), 0))

    @property
    def tiene_pago_en_efectivo(self) -> bool:
        return any(pago.medio is MedioPago.EFECTIVO for pago in self.pagos)

    @property
    def total_a_cobrar(self) -> Dinero:
        """Total que deben sumar los pagos para cerrar la venta.

        Se redondea a la decena solo si hay un pago en efectivo (HU-VTA-04); con
        solo tarjeta/transferencia/credito, el total se cobra exacto.
        """
        if self.tiene_pago_en_efectivo:
            return Dinero(redondear_a_decena(self.total.monto))
        return self.total

    def agregar_pago(self, pago: Pago) -> None:
        self.pagos.append(pago)

    @property
    def total_pagado(self) -> Dinero:
        return Dinero(sum((pago.monto.monto for pago in self.pagos), 0))

    @property
    def vuelto_entregado(self) -> Dinero:
        """Vuelto total entregado en la venta (sale de la gaveta, no es venta)."""
        total = sum(
            pago.cobro_efectivo.vuelto.monto
            for pago in self.pagos
            if pago.cobro_efectivo is not None
        )
        return Dinero(total)

    def validar_cierre(self) -> None:
        """Valida que la venta pueda cerrarse (HU-VTA-03): no la muta ni cambia su estado."""
        if not self.detalles:
            raise ReglaVentaInvalida("No se puede cerrar una venta sin productos")
        if not self.pagos:
            raise ReglaVentaInvalida("No se puede cerrar una venta sin pagos registrados")
        if self.total_pagado.monto != self.total_a_cobrar.monto:
            raise ReglaVentaInvalida(
                f"La suma de los pagos (${self.total_pagado.monto}) no cubre "
                f"el total a cobrar (${self.total_a_cobrar.monto})"
            )
