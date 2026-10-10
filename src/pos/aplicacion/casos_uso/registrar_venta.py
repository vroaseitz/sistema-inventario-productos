"""Caso de uso: registrar una venta completa (HU-VTA-01, HU-VTA-03, HU-VTA-04).

El flujo de la pantalla de venta tiene tres pasos: abrir un ticket contra el turno
de caja en curso, agregar productos escaneados (uno o varios), y cerrarlo con uno
o mas pagos. Separarlo en tres metodos permite que la UI vaya mostrando el ticket
mientras se construye, sin tener que pasarle todo de una vez.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pos.aplicacion.puertos import (
    RepositorioExistencias,
    RepositorioProductos,
    RepositorioTurnosCaja,
    RepositorioVentas,
)
from pos.dominio.errores import DatosProductoInvalidos, ReglaCajaInvalida, ReglaVentaInvalida
from pos.dominio.pagos import Pago
from pos.dominio.ventas import DetalleVenta, Venta


@dataclass
class RegistrarVenta:
    repositorio_ventas: RepositorioVentas
    repositorio_turnos: RepositorioTurnosCaja
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias

    def iniciar(self, usuario_id: int, cliente_id: int | None = None) -> Venta:
        turno = self.repositorio_turnos.obtener_abierto()
        if turno is None:
            raise ReglaCajaInvalida(
                "No hay una jornada de caja abierta; no se pueden registrar ventas"
            )
        return Venta(turno_caja_id=turno.id, usuario_id=usuario_id, cliente_id=cliente_id)

    def agregar_producto(
        self, venta: Venta, codigo_producto: str, cantidad: Decimal | float = 1
    ) -> DetalleVenta:
        producto = self.repositorio_productos.obtener_por_codigo(codigo_producto)
        if producto is None:
            raise DatosProductoInvalidos(f"No existe un producto con codigo {codigo_producto}")
        costo_unitario = producto.costo.neto if producto.costo is not None else None
        return venta.agregar_detalle(codigo_producto, cantidad, producto.precio, costo_unitario)

    def agregar_pago(self, venta: Venta, pago: Pago) -> None:
        venta.agregar_pago(pago)

    def cerrar(self, venta: Venta) -> Venta:
        """Valida stock y pagos, descuenta existencias y persiste la venta completa."""
        venta.validar_cierre()

        faltantes = []
        for detalle in venta.detalles:
            existencia = self.repositorio_existencias.obtener(detalle.producto_codigo)
            disponible = existencia.cantidad if existencia is not None else Decimal("0")
            if disponible < detalle.cantidad:
                faltantes.append(
                    f"{detalle.producto_codigo} (hay {disponible}, se venden {detalle.cantidad})"
                )
        if faltantes:
            raise ReglaVentaInvalida(f"Stock insuficiente: {', '.join(faltantes)}")

        for detalle in venta.detalles:
            existencia = self.repositorio_existencias.obtener(detalle.producto_codigo)
            existencia.descontar(detalle.cantidad)
            self.repositorio_existencias.guardar(existencia)

        self.repositorio_ventas.guardar(venta)
        return venta
