"""Repositorio de usuarios sobre SQLite. Implementa RepositorioUsuarios."""

from __future__ import annotations

import sqlite3

from pos.dominio.usuarios import Rol, Usuario


class RepositorioUsuariosSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, usuario: Usuario) -> None:
        cursor = self._con.execute(
            "INSERT INTO usuarios (nombre, clave_hash, rol, activo) VALUES (?, ?, ?, ?)",
            (usuario.nombre, usuario.clave_hash, usuario.rol.value, int(usuario.activo)),
        )
        usuario.id = cursor.lastrowid

    def obtener_por_nombre(self, nombre: str) -> Usuario | None:
        fila = self._con.execute(
            "SELECT * FROM usuarios WHERE nombre = ?", (nombre.strip().lower(),)
        ).fetchone()
        if fila is None:
            return None
        return Usuario(
            fila["nombre"], fila["clave_hash"], Rol(fila["rol"]), bool(fila["activo"]), fila["id"]
        )

    def hay_usuarios(self) -> bool:
        return self._con.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None
