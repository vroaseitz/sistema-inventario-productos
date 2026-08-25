"""Creacion de la conexion SQLite del espejo local.

Se activa WAL (Write-Ahead Logging) para que lecturas y escrituras no se bloqueen
entre si y para que un corte de energia a mitad de una transaccion no corrompa la
base: SQLite en WAL es atomico y recuperable. Clave para un POS que debe seguir
vendiendo offline sin arriesgar los datos.
"""

from __future__ import annotations

import sqlite3


def crear_conexion(ruta: str) -> sqlite3.Connection:
    conexion = sqlite3.connect(ruta, isolation_level=None)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA journal_mode=WAL;")
    conexion.execute("PRAGMA foreign_keys=ON;")
    conexion.execute("PRAGMA synchronous=NORMAL;")
    return conexion
