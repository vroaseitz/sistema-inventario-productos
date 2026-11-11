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

    def actualizar(self, anterior: str, nombre: str, contacto: str) -> None:
        """Cambia nombre y contacto. Las facturas ya registradas siguen al proveedor (si no, su
        historial quedaria con un nombre que ya no existe). Todo o nada."""
        self._con.execute("BEGIN")
        try:
            cursor = self._con.execute(
                "UPDATE proveedores SET nombre = ?, contacto = ? WHERE nombre = ?",
                (nombre, contacto, anterior),
            )
            if cursor.rowcount == 0:  # solo existia por sus facturas: ahora tambien se guarda
                self._con.execute(
                    "INSERT INTO proveedores (nombre, contacto) VALUES (?, ?)", (nombre, contacto)
                )
            self._con.execute(
                "UPDATE facturas_compra SET proveedor = ? WHERE proveedor = ? COLLATE NOCASE",
                (nombre, anterior),
            )
        except Exception:
            self._con.execute("ROLLBACK")
            raise
        self._con.execute("COMMIT")

    def listar(self) -> list[Proveedor]:
        filas = self._con.execute(
            "SELECT id, nombre, contacto FROM proveedores ORDER BY nombre COLLATE NOCASE"
        ).fetchall()
        return [Proveedor(f["nombre"], f["contacto"], f["id"]) for f in filas]
