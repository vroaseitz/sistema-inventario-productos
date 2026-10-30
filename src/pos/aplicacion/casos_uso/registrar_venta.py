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
    ColaSincronizacion,
    RepositorioExistencias,
    RepositorioLotes,
    RepositorioProductos,
    RepositorioTurnosCaja,
    RepositorioVentas,
)
from pos.aplicacion.sincronizacion import encolar_existencia, encolar_lote, encolar_venta
from pos.dominio.errores import DatosProductoInvalidos, ReglaCajaInvalida, ReglaVentaInvalida
from pos.dominio.lotes import Lote, consumir_fefo, proponer_lote
from pos.dominio.pagos import Pago
from pos.dominio.productos import UnidadVenta
from pos.dominio.ventas import DetalleVenta, Venta


@dataclass
class RegistrarVenta:
    repositorio_ventas: RepositorioVentas
    repositorio_turnos: RepositorioTurnosCaja
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias
    cola: ColaSincronizacion | None = None
    repositorio_lotes: RepositorioLotes | None = None

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

        cantidad_dec = Decimal(str(cantidad))
        if producto.unidad_venta is UnidadVenta.UNIDAD and cantidad_dec % 1 != 0:
            raise DatosProductoInvalidos(
                "Un producto por unidad requiere una cantidad entera "
                "(solo a granel admite decimales)"
            )

        # HU-INV-01: avisar al agregar el producto, no recien al cerrar la venta
        # (antes se podia armar un ticket entero con un producto sin stock y
        # quedaba bloqueado al cobrar, sin forma de sacar la linea).
        ya_en_ticket = next(
            (d.cantidad for d in venta.detalles if d.producto_codigo == codigo_producto),
            Decimal("0"),
        )
        existencia = self.repositorio_existencias.obtener(codigo_producto)
        disponible = existencia.cantidad if existencia is not None else Decimal("0")
        pedido_total = ya_en_ticket + cantidad_dec
        if pedido_total > disponible:
            raise ReglaVentaInvalida(
                f"Stock insuficiente de {codigo_producto}: "
                f"hay {disponible}, se pedirian {pedido_total}"
            )

        costo_unitario = producto.costo.neto if producto.costo is not None else None
        return venta.agregar_detalle(codigo_producto, cantidad_dec, producto.precio, costo_unitario)

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
            encolar_existencia(self.cola, existencia)
            self._consumir_lotes(
                detalle.producto_codigo,
                detalle.cantidad,
                venta.lote_elegido.get(detalle.producto_codigo),
            )

        self.repositorio_ventas.guardar(venta)
        turno = self.repositorio_turnos.obtener_abierto()
        if turno is not None:
            encolar_venta(self.cola, venta, turno.uuid)
        return venta

    def lotes_de(self, codigo: str) -> list[Lote]:
        """Lotes con saldo del producto, el que vence antes primero."""
        if self.repositorio_lotes is None:
            return []
        lotes = [x for x in self.repositorio_lotes.por_producto(codigo) if x.saldo > 0]
        return sorted(lotes, key=lambda x: x.fecha_vencimiento)

    def lote_para(self, venta: Venta, codigo: str) -> Lote | None:
        """Lote que se propone en la linea (I-03): el elegido o el que vence antes."""
        return proponer_lote(self.lotes_de(codigo), venta.lote_elegido.get(codigo))

    def elegir_lote(self, venta: Venta, codigo: str, lote_uuid: str) -> None:
        if all(x.uuid != lote_uuid for x in self.lotes_de(codigo)):
            raise ReglaVentaInvalida("Ese lote no tiene saldo para este producto")
        venta.lote_elegido[codigo] = lote_uuid

    def _consumir_lotes(self, codigo: str, cantidad: Decimal, preferido: str | None = None) -> None:
        """Descuenta de los lotes primero el que vence antes (FEFO) y sincroniza lo cambiado."""
        if self.repositorio_lotes is None:
            return
        lotes = [lote for lote in self.repositorio_lotes.por_producto(codigo) if lote.saldo > 0]
        antes = {lote.uuid: lote.saldo for lote in lotes}
        consumir_fefo(lotes, cantidad, preferido)
        for lote in lotes:
            if lote.saldo != antes[lote.uuid]:
                self.repositorio_lotes.guardar(lote)
                encolar_lote(self.cola, lote)
