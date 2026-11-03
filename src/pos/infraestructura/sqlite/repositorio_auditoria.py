"""Registro de auditoria sobre SQLite. Implementa RepositorioAuditoria."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime


class RepositorioAuditoriaSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def registrar(
        self,
        usuario: str,
        accion: str,
        detalle: dict,
        registro: str = "",
        antes: str = "",
        despues: str = "",
    ) -> None:
        self._con.execute(
            "INSERT INTO auditoria (fecha, usuario, accion, detalle, registro, antes, despues) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                usuario,
                accion,
                json.dumps(detalle, ensure_ascii=False),
                registro,
                antes,
                despues,
            ),
        )
        self._con.commit()

    def listar(
        self,
        accion: str | None = None,
        usuario: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[dict]:
        condiciones, parametros = [], []
        if accion is not None:
            condiciones.append("accion = ?")
            parametros.append(accion)
        if usuario is not None:
            condiciones.append("usuario = ?")
            parametros.append(usuario)
        if desde is not None:
            condiciones.append("date(fecha) >= ?")
            parametros.append(desde.isoformat())
        if hasta is not None:
            condiciones.append("date(fecha) <= ?")
            parametros.append(hasta.isoformat())
        consulta = "SELECT * FROM auditoria"
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        filas = self._con.execute(consulta + " ORDER BY id DESC", parametros).fetchall()
        return [
            {
                "fecha": f["fecha"],
                "usuario": f["usuario"],
                "accion": f["accion"],
                "detalle": json.loads(f["detalle"]),
                "registro": f["registro"],
                "antes": f["antes"],
                "despues": f["despues"],
            }
            for f in filas
        ]
