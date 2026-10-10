"""Repositorio de ventas sobre SQLite. Implementa RepositorioVentas.

Una venta toca tres tablas (venta, detalles, pagos). La conexion del espejo local
corre en autocommit (`isolation_level=None`, ver `conexion.py`), asi que el insert
se envuelve en una transaccion explicita: si algo falla a mitad de camino (p. ej.
un pago mal formado), no debe quedar una venta persistida sin sus lineas o sin
sus pagos.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal

from pos.dominio.pagos import CobroEfectivo, ConteoDenominaciones, MedioPago, Pago
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import DetalleVenta, EstadoVenta, Venta


class RepositorioVentasSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, venta: Venta) -> None:
        if venta.id is not None:
            raise NotImplementedError("Modificar una venta ya guardada no esta soportado aun")

        self._con.execute("BEGIN")
        try:
            cursor = self._con.execute(
                """
                INSERT INTO ventas (turno_caja_id, usuario_id, cliente_id, estado, creado_en)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    venta.turno_caja_id,
                    venta.usuario_id,
                    venta.cliente_id,
                    venta.estado.value,
                    venta.creado_en.isoformat(sep=" "),
                ),
            )
            venta.id = cursor.lastrowid

            for detalle in venta.detalles:
                self._con.execute(
                    """
                    INSERT INTO venta_detalles
                        (venta_id, producto_codigo, cantidad, precio_unitario,
                         costo_unitario, descuento_linea)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        venta.id,
                        detalle.producto_codigo,
                        str(detalle.cantidad),
                        detalle.precio_unitario.monto,
                        detalle.costo_unitario.monto if detalle.costo_unitario else None,
                        detalle.descuento_linea.monto,
                    ),
                )

            for pago in venta.pagos:
                monto_entregado = None
                composicion_json = None
                if pago.cobro_efectivo is not None:
                    monto_entregado = pago.cobro_efectivo.monto_entregado.monto
                    if pago.cobro_efectivo.composicion_entregada is not None:
                        composicion_json = json.dumps(
                            pago.cobro_efectivo.composicion_entregada.conteo
                        )
                self._con.execute(
                    """
                    INSERT INTO venta_pagos
                        (venta_id, medio_pago, monto, monto_entregado, composicion_entregada)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        venta.id,
                        pago.medio.value,
                        pago.monto.monto,
                        monto_entregado,
                        composicion_json,
                    ),
                )
        except Exception:
            self._con.execute("ROLLBACK")
            venta.id = None
            raise
        else:
            self._con.execute("COMMIT")

    def obtener_por_turno(self, turno_caja_id: int) -> list[Venta]:
        filas_venta = self._con.execute(
            "SELECT * FROM ventas WHERE turno_caja_id = ? ORDER BY id", (turno_caja_id,)
        ).fetchall()
        return [self._a_venta(f) for f in filas_venta]

    def _a_venta(self, fila: sqlite3.Row) -> Venta:
        detalles_filas = self._con.execute(
            "SELECT * FROM venta_detalles WHERE venta_id = ? ORDER BY id", (fila["id"],)
        ).fetchall()
        detalles = [
            DetalleVenta(
                producto_codigo=d["producto_codigo"],
                cantidad=Decimal(d["cantidad"]),
                precio_unitario=Dinero(d["precio_unitario"]),
                costo_unitario=(
                    Dinero(d["costo_unitario"]) if d["costo_unitario"] is not None else None
                ),
                descuento_linea=Dinero(d["descuento_linea"]),
            )
            for d in detalles_filas
        ]

        pagos_filas = self._con.execute(
            "SELECT * FROM venta_pagos WHERE venta_id = ? ORDER BY id", (fila["id"],)
        ).fetchall()
        pagos = []
        for p in pagos_filas:
            medio = MedioPago(p["medio_pago"])
            cobro_efectivo = None
            if medio is MedioPago.EFECTIVO and p["monto_entregado"] is not None:
                composicion = None
                if p["composicion_entregada"] is not None:
                    crudo = json.loads(p["composicion_entregada"])
                    composicion = ConteoDenominaciones({int(k): v for k, v in crudo.items()})
                entregado = p["monto_entregado"]
                redondeado = p["monto"]
                # El total sin redondear y la diferencia de redondeo no se persisten
                # por separado (no hace falta otra columna para el arqueo, que solo
                # usa monto/monto_entregado/vuelto); al recargar, se aproximan al
                # monto ya redondeado. Si se necesita el detalle fino para un reporte
                # de diferencias de redondeo, agregar una columna propia.
                cobro_efectivo = CobroEfectivo(
                    total_sin_redondear=Dinero(redondeado),
                    total_redondeado=Dinero(redondeado),
                    diferencia_redondeo=0,
                    monto_entregado=Dinero(entregado),
                    vuelto=Dinero(entregado - redondeado),
                    composicion_entregada=composicion,
                )
            pagos.append(Pago(medio=medio, monto=Dinero(p["monto"]), cobro_efectivo=cobro_efectivo))

        return Venta(
            id=fila["id"],
            turno_caja_id=fila["turno_caja_id"],
            usuario_id=fila["usuario_id"],
            cliente_id=fila["cliente_id"],
            detalles=detalles,
            pagos=pagos,
            estado=EstadoVenta(fila["estado"]),
            creado_en=datetime.fromisoformat(fila["creado_en"]),
        )
