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
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

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
                INSERT INTO ventas
                    (turno_caja_id, usuario_id, cliente_id, estado, creado_en, uuid, nota)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    venta.turno_caja_id,
                    venta.usuario_id,
                    venta.cliente_id,
                    venta.estado.value,
                    venta.creado_en.isoformat(sep=" "),
                    venta.uuid,
                    venta.nota,
                ),
            )
            venta.id = cursor.lastrowid

            for detalle in venta.detalles:
                self._con.execute(
                    """
                    INSERT INTO venta_detalles
                        (venta_id, producto_codigo, cantidad, precio_unitario,
                         costo_unitario, descuento_linea, motivo_descuento)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        venta.id,
                        detalle.producto_codigo,
                        str(detalle.cantidad),
                        detalle.precio_unitario.monto,
                        detalle.costo_unitario.monto if detalle.costo_unitario else None,
                        detalle.descuento_linea.monto,
                        detalle.motivo_descuento,
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

    def obtener(self, venta_id: int) -> Venta | None:
        fila = self._con.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        return self._a_venta(fila) if fila else None

    def marcar_anulada(self, venta: Venta) -> None:
        """HU-VTA-11: la venta se conserva; solo cambia su estado y queda el motivo y quien fue."""
        if venta.id is None:
            raise ValueError("La venta no esta guardada")
        self._con.execute(
            "UPDATE ventas SET estado = ?, motivo_anulacion = ?, anulada_por = ?, anulada_en = ? "
            "WHERE id = ? AND estado = 'pagada'",
            (
                venta.estado.value,
                venta.motivo_anulacion,
                venta.anulada_por,
                venta.anulada_en.isoformat(sep=" ") if venta.anulada_en else None,
                venta.id,
            ),
        )
        self._con.commit()

    def guardar_consumo_lotes(
        self, venta_id: int, consumos: list[tuple[str, str, Decimal]]
    ) -> None:
        """De que lote salio cada cantidad (codigo del producto, uuid del lote, cantidad)."""
        for codigo, lote_uuid, cantidad in consumos:
            self._con.execute(
                "INSERT INTO venta_lotes (venta_id, producto_codigo, lote_uuid, cantidad) "
                "VALUES (?, ?, ?, ?)",
                (venta_id, codigo, lote_uuid, str(cantidad)),
            )
        self._con.commit()

    def consumo_lotes(self, venta_id: int) -> list[tuple[str, str, Decimal]]:
        filas = self._con.execute(
            "SELECT producto_codigo, lote_uuid, cantidad FROM venta_lotes "
            "WHERE venta_id = ? ORDER BY id",
            (venta_id,),
        ).fetchall()
        return [(f["producto_codigo"], f["lote_uuid"], Decimal(f["cantidad"])) for f in filas]

    def obtener_por_turno(self, turno_caja_id: int) -> list[Venta]:
        return self._ventas_donde("v.turno_caja_id = ?", (turno_caja_id,))

    def ultima(self) -> Venta | None:
        """Ultima venta pagada (para reimprimir el ultimo comprobante)."""
        fila = self._con.execute(
            "SELECT * FROM ventas WHERE estado = 'pagada' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return self._a_venta(fila) if fila else None

    def ultima_venta_por_producto(self) -> dict[str, date]:
        """Fecha de la ultima venta pagada de cada producto (para la rotacion)."""
        filas = self._con.execute(
            "SELECT d.producto_codigo AS codigo, MAX(v.creado_en) AS ultima "
            "FROM venta_detalles d JOIN ventas v ON v.id = d.venta_id "
            "WHERE v.estado = 'pagada' GROUP BY d.producto_codigo"
        ).fetchall()
        # creado_en es "AAAA-MM-DD hh:mm:ss": basta con los 10 primeros caracteres (la fecha).
        return {f["codigo"]: date.fromisoformat(f["ultima"][:10]) for f in filas}

    def por_periodo(self, desde: date, hasta: date) -> list[Venta]:
        """Ventas pagadas con fecha entre `desde` y `hasta`, ambas inclusive.

        Se compara el texto de `creado_en` contra el inicio de `desde` y el de `hasta + 1 dia`
        (sirve tanto con "AAAA-MM-DD hh:mm" como con "AAAA-MM-DDThh:mm") para poder usar el indice;
        envolver la columna en `date(...)` lo impedia.
        """
        return self._ventas_donde(
            "v.estado = 'pagada' AND v.creado_en >= ? AND v.creado_en < ?",
            (desde.isoformat(), (hasta + timedelta(days=1)).isoformat()),
        )

    def _ventas_donde(self, condicion: str, parametros: tuple) -> list[Venta]:
        """Carga ventas con sus lineas y pagos en 3 consultas (no 1 + 2 por venta)."""
        filas = self._con.execute(
            f"SELECT v.* FROM ventas v WHERE {condicion} ORDER BY v.id", parametros
        ).fetchall()
        if not filas:
            return []
        detalles: dict[int, list[sqlite3.Row]] = defaultdict(list)
        for d in self._con.execute(
            "SELECT d.* FROM venta_detalles d JOIN ventas v ON v.id = d.venta_id "
            f"WHERE {condicion} ORDER BY d.id",
            parametros,
        ):
            detalles[d["venta_id"]].append(d)
        pagos: dict[int, list[sqlite3.Row]] = defaultdict(list)
        for p in self._con.execute(
            "SELECT p.* FROM venta_pagos p JOIN ventas v ON v.id = p.venta_id "
            f"WHERE {condicion} ORDER BY p.id",
            parametros,
        ):
            pagos[p["venta_id"]].append(p)
        return [self._a_venta(f, detalles[f["id"]], pagos[f["id"]]) for f in filas]

    def _a_venta(
        self,
        fila: sqlite3.Row,
        detalles_filas: list[sqlite3.Row] | None = None,
        pagos_filas: list[sqlite3.Row] | None = None,
    ) -> Venta:
        if detalles_filas is None:
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
                motivo_descuento=d["motivo_descuento"] or "",
            )
            for d in detalles_filas
        ]

        if pagos_filas is None:
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
            uuid=fila["uuid"] or str(uuid4()),
            turno_caja_id=fila["turno_caja_id"],
            usuario_id=fila["usuario_id"],
            cliente_id=fila["cliente_id"],
            detalles=detalles,
            pagos=pagos,
            estado=EstadoVenta(fila["estado"]),
            creado_en=datetime.fromisoformat(fila["creado_en"]),
            nota=fila["nota"] or "",
            motivo_anulacion=fila["motivo_anulacion"] or "",
            anulada_por=fila["anulada_por"] or "",
            anulada_en=(datetime.fromisoformat(fila["anulada_en"]) if fila["anulada_en"] else None),
        )
