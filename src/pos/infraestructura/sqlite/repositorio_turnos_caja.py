"""Repositorio de turnos de caja sobre SQLite. Implementa RepositorioTurnosCaja."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from pos.dominio.caja import MovimientoCaja, TipoMovimientoCaja, TurnoCaja
from pos.dominio.pagos import ConteoDenominaciones
from pos.dominio.value_objects import Dinero


class RepositorioTurnosCajaSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, turno: TurnoCaja) -> None:
        composicion_json = (
            json.dumps(turno.composicion_fondo_inicial.conteo)
            if turno.composicion_fondo_inicial is not None
            else None
        )
        if turno.id is None:
            cursor = self._con.execute(
                """
                INSERT INTO turnos_caja (usuario_id, fondo_inicial, composicion_fondo, abierto_en)
                VALUES (?, ?, ?, ?)
                """,
                (
                    turno.usuario_id,
                    turno.fondo_inicial.monto,
                    composicion_json,
                    turno.abierto_en.isoformat(sep=" "),
                ),
            )
            turno.id = cursor.lastrowid
        else:
            self._con.execute(
                "UPDATE turnos_caja SET cerrado_en = ? WHERE id = ?",
                (
                    turno.cerrado_en.isoformat(sep=" ") if turno.cerrado_en else None,
                    turno.id,
                ),
            )

    def obtener_abierto(self) -> TurnoCaja | None:
        fila = self._con.execute(
            "SELECT * FROM turnos_caja WHERE cerrado_en IS NULL"
        ).fetchone()
        if not fila:
            return None
        return self._a_turno(fila)

    def registrar_movimiento(self, turno_id: int, movimiento: MovimientoCaja) -> None:
        self._con.execute(
            """
            INSERT INTO movimientos_caja (turno_id, tipo, monto, motivo, creado_en)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                turno_id,
                movimiento.tipo.value,
                movimiento.monto.monto,
                movimiento.motivo,
                movimiento.creado_en.isoformat(sep=" "),
            ),
        )

    def _a_turno(self, fila: sqlite3.Row) -> TurnoCaja:
        composicion = None
        if fila["composicion_fondo"] is not None:
            crudo = json.loads(fila["composicion_fondo"])
            composicion = ConteoDenominaciones({int(k): v for k, v in crudo.items()})

        movimientos_filas = self._con.execute(
            "SELECT * FROM movimientos_caja WHERE turno_id = ? ORDER BY id", (fila["id"],)
        ).fetchall()
        movimientos = [
            MovimientoCaja(
                tipo=TipoMovimientoCaja(m["tipo"]),
                monto=Dinero(m["monto"]),
                motivo=m["motivo"],
                creado_en=datetime.fromisoformat(m["creado_en"]),
            )
            for m in movimientos_filas
        ]

        return TurnoCaja(
            id=fila["id"],
            usuario_id=fila["usuario_id"],
            fondo_inicial=Dinero(fila["fondo_inicial"]),
            composicion_fondo_inicial=composicion,
            abierto_en=datetime.fromisoformat(fila["abierto_en"]),
            cerrado_en=datetime.fromisoformat(fila["cerrado_en"]) if fila["cerrado_en"] else None,
            movimientos=movimientos,
        )
