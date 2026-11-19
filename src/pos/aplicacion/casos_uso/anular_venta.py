"""Caso de uso: anular una venta ya cobrada, con motivo, sin borrarla (HU-VTA-11).

Al anular: la venta queda marcada (se conserva), la existencia de cada producto vuelve al lote del
que salio con un movimiento de reversa, si se pago a credito el consumo se revierte en la cuenta del
cliente, el cierre de la jornada la cuenta aparte y la auditoria guarda quien, cuando y por que.

CL-06 (PO, 17-11): si la venta se pago con dinero, hay que decir que se hace con el:
devolucion en efectivo (sale de la caja del dia como retiro «Devolución»), saldo a favor del cliente
(solo si la venta tiene cliente) o cambio por otro producto (el efectivo sale igual que en la
devolucion y se cobra el reemplazo en una venta nueva).

Solo se anulan ventas de la jornada abierta: asi el cierre y el efectivo de la gaveta no cambian
despues del corte. Una venta ya anulada no se anula de nuevo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioClientes,
    RepositorioExistencias,
    RepositorioLotes,
    RepositorioTurnosCaja,
    RepositorioVentas,
)
from pos.aplicacion.registro_movimientos import RegistroMovimientos
from pos.aplicacion.sincronizacion import (
    encolar_anulacion_venta,
    encolar_existencia,
    encolar_lote,
    encolar_movimiento_cliente,
)
from pos.dominio.caja import TipoMovimientoCaja
from pos.dominio.clientes import (
    MEDIO_ANULACION,
    MEDIO_SALDO_A_FAVOR,
    MovimientoCliente,
    TipoMovimientoCliente,
)
from pos.dominio.errores import ReglaVentaInvalida
from pos.dominio.formato import formatear_clp
from pos.dominio.inventario import TipoMovimiento
from pos.dominio.pagos import MedioPago
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import DestinoDevolucion, EstadoVenta, Venta, texto_del_motivo


@dataclass
class AnularVenta:
    repositorio_ventas: RepositorioVentas
    repositorio_turnos: RepositorioTurnosCaja
    repositorio_existencias: RepositorioExistencias
    cola: ColaSincronizacion | None = None
    repositorio_lotes: RepositorioLotes | None = None
    repositorio_clientes: RepositorioClientes | None = None
    movimientos: RegistroMovimientos | None = None
    auditor: Auditor | None = None
    registrar_movimiento_caja: RegistrarMovimientoCaja | None = None

    def opciones_de_devolucion(self, venta: Venta) -> list[DestinoDevolucion]:
        """Que se le puede ofrecer al cliente segun como pago (vacio = no hay dinero)."""
        opciones = []
        if venta.monto_en_efectivo > 0:
            opciones += [DestinoDevolucion.EFECTIVO, DestinoDevolucion.CAMBIO]
        if venta.cliente_id is not None and venta.monto_pagado_sin_credito > 0:
            opciones.append(DestinoDevolucion.SALDO_A_FAVOR)
        return opciones

    def ejecutar(
        self,
        venta_id: int,
        motivo: str,
        detalle: str,
        usuario: str,
        destino: DestinoDevolucion | None = None,
    ) -> Venta:
        venta = self.repositorio_ventas.obtener(venta_id)
        if venta is None:
            raise ReglaVentaInvalida("La venta no existe")
        if venta.estado is EstadoVenta.ANULADA:
            raise ReglaVentaInvalida("Esta venta ya está anulada: no se puede anular de nuevo")
        turno = self.repositorio_turnos.obtener_abierto()
        if turno is None or venta.turno_caja_id != turno.id:
            raise ReglaVentaInvalida(
                "Solo se pueden anular ventas de la jornada abierta. "
                "Para una venta de un día anterior, hay que corregirla con el cierre de ese día."
            )
        motivo_final = texto_del_motivo(motivo, detalle)  # valida la lista y el «Otro»
        opciones = self.opciones_de_devolucion(venta)
        if opciones and destino is None:
            raise ReglaVentaInvalida("Elige qué se hace con el dinero del cliente")
        if destino is not None and destino not in opciones:
            raise ReglaVentaInvalida(self._por_que_no(venta, destino))
        venta.anular(motivo_final, usuario)

        self._restituir_existencias(venta)
        self._revertir_credito(venta)
        self._devolver_dinero(venta, destino)
        self.repositorio_ventas.marcar_anulada(venta)
        encolar_anulacion_venta(self.cola, venta)
        if self.auditor is not None:
            self.auditor.registrar(
                "Anulación de venta",
                f"Venta N° {venta.id} · {formatear_clp(venta.total.monto)}",
                "pagada",
                f"anulada ({motivo_final})" + (f" · {destino.value}" if destino else ""),
            )
        return venta

    @staticmethod
    def _por_que_no(venta: Venta, destino: DestinoDevolucion) -> str:
        if destino is DestinoDevolucion.SALDO_A_FAVOR and venta.cliente_id is None:
            return "El saldo a favor solo se puede dejar si la venta tiene un cliente"
        if destino in (DestinoDevolucion.EFECTIVO, DestinoDevolucion.CAMBIO):
            return "La venta no se pagó en efectivo: no hay efectivo que devolver de la caja"
        return "Esa opción no corresponde a esta venta"

    def _devolver_dinero(self, venta: Venta, destino: DestinoDevolucion | None) -> None:
        """Lo que pasa con el dinero segun lo elegido (CL-06). Sin destino no hay dinero."""
        if destino is DestinoDevolucion.SALDO_A_FAVOR:
            self._dejar_saldo_a_favor(venta)
        elif destino in (DestinoDevolucion.EFECTIVO, DestinoDevolucion.CAMBIO):
            if self.registrar_movimiento_caja is None:
                raise ReglaVentaInvalida("No se puede registrar la salida de caja")
            texto = (
                "Devolución" if destino is DestinoDevolucion.EFECTIVO else "Devolución por cambio"
            )
            self.registrar_movimiento_caja.ejecutar(
                TipoMovimientoCaja.RETIRO,
                Dinero(venta.monto_en_efectivo),
                f"{texto} · venta N° {venta.id}",
            )

    def _dejar_saldo_a_favor(self, venta: Venta) -> None:
        if self.repositorio_clientes is None or venta.cliente_id is None:
            raise ReglaVentaInvalida("El saldo a favor solo se puede dejar si hay un cliente")
        movimiento = MovimientoCliente(
            cliente_id=venta.cliente_id,
            tipo=TipoMovimientoCliente.ABONO,
            monto=venta.monto_pagado_sin_credito,
            fecha=venta.anulada_en.date() if venta.anulada_en else venta.creado_en.date(),
            detalle=f"Saldo a favor por la anulación de la venta N° {venta.id}",
            medio=MEDIO_SALDO_A_FAVOR,
        )
        self.repositorio_clientes.agregar_movimiento(movimiento)
        cliente = self.repositorio_clientes.obtener(venta.cliente_id)
        if cliente is not None:
            encolar_movimiento_cliente(self.cola, cliente, movimiento)

    def _restituir_existencias(self, venta: Venta) -> None:
        por_lote: dict[str, Decimal] = {}
        for _codigo, lote_uuid, cantidad in self.repositorio_ventas.consumo_lotes(venta.id):
            por_lote[lote_uuid] = por_lote.get(lote_uuid, Decimal("0")) + cantidad
        for detalle in venta.detalles:
            existencia = self.repositorio_existencias.obtener(detalle.producto_codigo)
            if existencia is not None:
                existencia.ingresar(detalle.cantidad)
                self.repositorio_existencias.guardar(existencia)
                encolar_existencia(self.cola, existencia)
            if self.movimientos is not None:
                self.movimientos.registrar(
                    detalle.producto_codigo,
                    TipoMovimiento.ANULACION,
                    detalle.cantidad,
                    f"Anulación del ticket {venta.id}",
                )
        if self.repositorio_lotes is None:
            return
        for lote_uuid, cantidad in por_lote.items():
            lote = self.repositorio_lotes.obtener_por_uuid(lote_uuid)
            if lote is not None:  # el saldo vuelve al lote del que salio
                lote.saldo += cantidad
                self.repositorio_lotes.guardar(lote)
                encolar_lote(self.cola, lote)

    def _revertir_credito(self, venta: Venta) -> None:
        credito = sum(p.monto.monto for p in venta.pagos if p.medio is MedioPago.CREDITO_CLIENTE)
        if not credito or self.repositorio_clientes is None or venta.cliente_id is None:
            return
        movimiento = MovimientoCliente(
            cliente_id=venta.cliente_id,
            tipo=TipoMovimientoCliente.ABONO,
            monto=credito,
            fecha=venta.anulada_en.date() if venta.anulada_en else venta.creado_en.date(),
            detalle=f"Anulación de la venta N° {venta.id}",
            medio=MEDIO_ANULACION,
        )
        self.repositorio_clientes.agregar_movimiento(movimiento)
        cliente = self.repositorio_clientes.obtener(venta.cliente_id)
        if cliente is not None:
            encolar_movimiento_cliente(self.cola, cliente, movimiento)
