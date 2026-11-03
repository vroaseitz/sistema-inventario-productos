"""Repositorio de proveedores sobre SQLite. Implementa RepositorioProveedores."""

from __future__ import annotations

import sqlite3

from pos.dominio.compras import Proveedor


class RepositorioProveedoresSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def agregar(self, nombre: str, contacto: str = "") -> bool:
        """Crea el proveedor; devuelve False si ya existia (sin distinguir mayusculas)."""
        cursor = self._con.execute(
            "INSERT OR IGNORE INTO proveedores (nombre, contacto) VALUES (?, ?)",
            (nombre, contacto),
        )
        return cursor.rowcount == 1

    def listar(self) -> list[Proveedor]:
        filas = self._con.execute(
            "SELECT id, nombre, contacto FROM proveedores ORDER BY nombre COLLATE NOCASE"
        ).fetchall()
        return [Proveedor(f["nombre"], f["contacto"], f["id"]) for f in filas]
