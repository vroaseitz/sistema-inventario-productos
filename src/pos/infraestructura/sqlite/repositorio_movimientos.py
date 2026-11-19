"""Historial de movimientos de inventario sobre SQLite. Implementa RepositorioMovimientos."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal

from pos.dominio.inventario import MovimientoInventario, TipoMovimiento


class RepositorioMovimientosSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def registrar(self, movimiento: MovimientoInventario) -> None:
        cursor = self._con.execute(
            "INSERT INTO movimientos_inventario (fecha, codigo_producto, tipo, cantidad, motivo, "
            "usuario) VALUES (?, ?, ?, ?, ?, ?)",
            (
                movimiento.fecha.isoformat(timespec="seconds"),
                movimiento.codigo_producto,
                movimiento.tipo.value,
                str(movimiento.cantidad),
                movimiento.motivo,
                movimiento.usuario,
            ),
        )
        movimiento.id = cursor.lastrowid
        self._con.commit()

    def listar(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        tipo: TipoMovimiento | None = None,
        codigo: str | None = None,
    ) -> list[MovimientoInventario]:
        condiciones, parametros = [], []
        if desde is not None:
            condiciones.append("date(fecha) >= ?")
            parametros.append(desde.isoformat())
        if hasta is not None:
            condiciones.append("date(fecha) <= ?")
            parametros.append(hasta.isoformat())
        if tipo is not None:
            condiciones.append("tipo = ?")
            parametros.append(tipo.value)
        if codigo is not None:
            condiciones.append("codigo_producto = ?")
            parametros.append(codigo)
        consulta = "SELECT * FROM movimientos_inventario"
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        filas = self._con.execute(consulta + " ORDER BY id DESC", parametros).fetchall()
        return [
            MovimientoInventario(
                f["codigo_producto"],
                TipoMovimiento(f["tipo"]),
                Decimal(f["cantidad"]),
                f["motivo"],
                f["usuario"],
                datetime.fromisoformat(f["fecha"]),
                f["id"],
            )
            for f in filas
        ]
