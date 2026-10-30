"""Tickets de venta abiertos sin cobrar (O-25): se guardan para no perderlos al cerrar."""

from __future__ import annotations

import json
import sqlite3


class RepositorioTicketsEsperaSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, tickets: list[dict]) -> None:
        """Reemplaza lo guardado por los tickets actuales (productos y lote elegido)."""
        self._con.execute("BEGIN")
        try:
            self._con.execute("DELETE FROM tickets_en_espera")
            for ticket in tickets:
                self._con.execute(
                    "INSERT INTO tickets_en_espera (datos_json) VALUES (?)",
                    (json.dumps(ticket),),
                )
        except Exception:
            self._con.execute("ROLLBACK")
            raise
        self._con.execute("COMMIT")

    def cargar(self) -> list[dict]:
        filas = self._con.execute("SELECT datos_json FROM tickets_en_espera ORDER BY id").fetchall()
        return [json.loads(f["datos_json"]) for f in filas]
