"""Repositorio de usuarios sobre SQLite. Implementa RepositorioUsuarios."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from pos.dominio.usuarios import Rol, Usuario


class RepositorioUsuariosSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, usuario: Usuario) -> None:
        """Crea el usuario o, si ya tiene id, actualiza clave, perfil y estado."""
        if usuario.id is None:
            cursor = self._con.execute(
                "INSERT INTO usuarios (nombre, clave_hash, rol, activo) VALUES (?, ?, ?, ?)",
                (usuario.nombre, usuario.clave_hash, usuario.rol.value, int(usuario.activo)),
            )
            usuario.id = cursor.lastrowid
        else:
            self._con.execute(
                "UPDATE usuarios SET clave_hash = ?, rol = ?, activo = ? WHERE id = ?",
                (usuario.clave_hash, usuario.rol.value, int(usuario.activo), usuario.id),
            )
        self._con.commit()

    def obtener_por_nombre(self, nombre: str) -> Usuario | None:
        fila = self._con.execute(
            "SELECT * FROM usuarios WHERE nombre = ?", (nombre.strip().lower(),)
        ).fetchone()
        return self._a_usuario(fila) if fila else None

    def listar(self) -> list[Usuario]:
        filas = self._con.execute("SELECT * FROM usuarios ORDER BY nombre").fetchall()
        return [self._a_usuario(f) for f in filas]

    def hay_usuarios(self) -> bool:
        return self._con.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None

    def registrar_acceso(self, usuario_id: int) -> None:
        self._con.execute(
            "UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), usuario_id),
        )
        self._con.commit()

    @staticmethod
    def _a_usuario(fila: sqlite3.Row) -> Usuario:
        acceso = fila["ultimo_acceso"]
        return Usuario(
            fila["nombre"],
            fila["clave_hash"],
            Rol(fila["rol"]),
            bool(fila["activo"]),
            fila["id"],
            datetime.fromisoformat(acceso) if acceso else None,
        )
