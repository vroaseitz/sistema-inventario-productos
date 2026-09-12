"""Repositorio de existencias sobre SQLite. Implementa RepositorioExistencias."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from pos.dominio.inventario import Existencia


class RepositorioExistenciasSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def obtener(self, codigo_producto: str) -> Existencia | None:
        fila = self._con.execute(
            "SELECT * FROM existencias WHERE codigo_producto = ?", (codigo_producto,)
        ).fetchone()
        if not fila:
            return None
        return Existencia(fila["codigo_producto"], Decimal(fila["cantidad"]))

    def guardar(self, existencia: Existencia) -> None:
        self._con.execute(
            """
            INSERT INTO existencias (codigo_producto, cantidad)
            VALUES (?, ?)
            ON CONFLICT(codigo_producto) DO UPDATE SET cantidad=excluded.cantidad
            """,
            (existencia.codigo_producto, str(existencia.cantidad)),
        )
