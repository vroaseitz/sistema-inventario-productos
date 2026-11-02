"""Registro de auditoria sobre SQLite. Implementa RepositorioAuditoria."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime


class RepositorioAuditoriaSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def registrar(self, usuario: str, accion: str, detalle: dict) -> None:
        self._con.execute(
            "INSERT INTO auditoria (fecha, usuario, accion, detalle) VALUES (?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                usuario,
                accion,
                json.dumps(detalle, ensure_ascii=False),
            ),
        )
        self._con.commit()

    def listar(self, accion: str | None = None) -> list[dict]:
        consulta = "SELECT fecha, usuario, accion, detalle FROM auditoria"
        parametros: tuple = ()
        if accion is not None:
            consulta += " WHERE accion = ?"
            parametros = (accion,)
        filas = self._con.execute(consulta + " ORDER BY id", parametros).fetchall()
        return [
            {
                "fecha": f["fecha"],
                "usuario": f["usuario"],
                "accion": f["accion"],
                "detalle": json.loads(f["detalle"]),
            }
            for f in filas
        ]
