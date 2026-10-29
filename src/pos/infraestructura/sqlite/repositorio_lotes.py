"""Repositorio de lotes sobre SQLite. Implementa RepositorioLotes."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from pos.dominio.lotes import Lote


class RepositorioLotesSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, lote: Lote) -> None:
        """Inserta el lote o actualiza su saldo/vencimiento (clave: uuid)."""
        self._con.execute(
            """
            INSERT INTO lotes (uuid, codigo_producto, fecha_vencimiento, saldo)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(uuid) DO UPDATE SET
                fecha_vencimiento = excluded.fecha_vencimiento,
                saldo = excluded.saldo
            """,
            (lote.uuid, lote.codigo_producto, lote.fecha_vencimiento.isoformat(), str(lote.saldo)),
        )
        if lote.id is None:
            fila = self._con.execute("SELECT id FROM lotes WHERE uuid = ?", (lote.uuid,)).fetchone()
            lote.id = fila["id"]

    def por_producto(self, codigo_producto: str) -> list[Lote]:
        filas = self._con.execute(
            "SELECT * FROM lotes WHERE codigo_producto = ? ORDER BY fecha_vencimiento, id",
            (codigo_producto,),
        ).fetchall()
        return [self._a_lote(f) for f in filas]

    def con_saldo(self) -> list[Lote]:
        filas = self._con.execute(
            "SELECT * FROM lotes WHERE CAST(saldo AS REAL) > 0 ORDER BY fecha_vencimiento, id"
        ).fetchall()
        return [self._a_lote(f) for f in filas]

    @staticmethod
    def _a_lote(fila: sqlite3.Row) -> Lote:
        return Lote(
            id=fila["id"],
            uuid=fila["uuid"],
            codigo_producto=fila["codigo_producto"],
            fecha_vencimiento=date.fromisoformat(fila["fecha_vencimiento"]),
            saldo=Decimal(fila["saldo"]),
        )
