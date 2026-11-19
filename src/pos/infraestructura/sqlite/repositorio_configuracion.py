"""Configuracion de operacion sobre SQLite. Implementa RepositorioConfiguracion."""

from __future__ import annotations

import sqlite3

from pos.dominio.configuracion import POR_CLAVE


class RepositorioConfiguracionSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def obtener(self, clave: str) -> int:
        """Valor guardado o, si nunca se cambio, el valor por defecto del parametro."""
        fila = self._con.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave,)
        ).fetchone()
        return int(fila["valor"]) if fila else POR_CLAVE[clave].defecto

    def guardar(self, clave: str, valor: int) -> None:
        self._con.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, str(valor)),
        )
        self._con.commit()

    def obtener_texto(self, clave: str, defecto: str = "") -> str:
        fila = self._con.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave,)
        ).fetchone()
        return fila["valor"] if fila else defecto

    def guardar_texto(self, clave: str, valor: str) -> None:
        self._con.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, valor.strip()),
        )
        self._con.commit()

    def restaurar_valores_por_defecto(self) -> None:
        self._con.execute("DELETE FROM configuracion")
        self._con.commit()
