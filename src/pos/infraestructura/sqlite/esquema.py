"""DDL del espejo local SQLite.

El esquema equivalente para PostgreSQL/Supabase vive en database/migraciones/.
"""

from __future__ import annotations

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS productos (
    codigo        TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    precio        INTEGER NOT NULL CHECK (precio >= 0),
    unidad_venta  TEXT NOT NULL DEFAULT 'unidad',
    categoria     TEXT,
    activo        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS existencias (
    codigo_producto TEXT PRIMARY KEY,
    cantidad        TEXT NOT NULL DEFAULT '0',
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);

-- Cola de operaciones pendientes de sincronizar con Supabase (modo offline).
-- id_cliente es un UUID generado en el cliente: permite sincronizacion idempotente
-- (ON CONFLICT DO NOTHING en el destino) aunque una operacion se reintente.
CREATE TABLE IF NOT EXISTS cola_sincronizacion (
    id_cliente TEXT PRIMARY KEY,
    entidad    TEXT NOT NULL,
    operacion  TEXT NOT NULL,
    datos_json TEXT NOT NULL,
    estado     TEXT NOT NULL DEFAULT 'pending',
    creado_en  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def crear_esquema(conexion: sqlite3.Connection) -> None:
    conexion.executescript(DDL)
