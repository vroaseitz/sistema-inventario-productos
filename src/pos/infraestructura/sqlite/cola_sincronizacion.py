"""Cola de sincronizacion offline sobre SQLite. Implementa ColaSincronizacion.

Diseno idempotente: cada operacion se identifica por un UUID de cliente. Reintentar
la sincronizacion no duplica datos porque el destino usa ese id como clave.
"""

from __future__ import annotations

import json
import sqlite3


class ColaSincronizacionSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def encolar(self, entidad: str, operacion: str, datos: dict, id_cliente: str) -> None:
        # ON CONFLICT DO NOTHING: si el mismo id_cliente se encola dos veces
        # (p. ej. tras un corte a mitad de proceso), no se duplica.
        self._con.execute(
            """
            INSERT INTO cola_sincronizacion (id_cliente, entidad, operacion, datos_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id_cliente) DO NOTHING
            """,
            (id_cliente, entidad, operacion, json.dumps(datos, ensure_ascii=False)),
        )

    def pendientes(self) -> list[dict]:
        # Orden por rowid = orden de insercion estricto. Se prefiere a creado_en, que
        # solo tiene resolucion de segundos y no desempata operaciones del mismo segundo.
        filas = self._con.execute(
            "SELECT * FROM cola_sincronizacion WHERE estado = 'pending' ORDER BY rowid"
        ).fetchall()
        return [
            {
                "id_cliente": f["id_cliente"],
                "entidad": f["entidad"],
                "operacion": f["operacion"],
                "datos": json.loads(f["datos_json"]),
            }
            for f in filas
        ]

    def marcar_sincronizada(self, id_cliente: str) -> None:
        self._con.execute(
            "UPDATE cola_sincronizacion SET estado = 'synced' WHERE id_cliente = ?",
            (id_cliente,),
        )
