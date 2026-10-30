"""DDL del espejo local SQLite.

El esquema equivalente para PostgreSQL/Supabase vive en database/migraciones/.
"""

from __future__ import annotations

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS categoria (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);

-- Seed inicial: las 4 categorias de siempre, con los mismos ids que usa
-- CATEGORIAS_VALIDAS. La lista definitiva la carga el negocio con
-- scripts/cargar_categorias.py cuando la Product Owner la valide.
INSERT OR IGNORE INTO categoria (id, nombre) VALUES (1, 'frutas');
INSERT OR IGNORE INTO categoria (id, nombre) VALUES (2, 'verduras');
INSERT OR IGNORE INTO categoria (id, nombre) VALUES (3, 'abarrotes');
INSERT OR IGNORE INTO categoria (id, nombre) VALUES (4, 'limpieza');

CREATE TABLE IF NOT EXISTS productos (
    codigo        TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    precio        INTEGER NOT NULL CHECK (precio >= 0),
    unidad_venta  TEXT NOT NULL DEFAULT 'unidad',
    categoria_id  INTEGER NOT NULL,
    activo        INTEGER NOT NULL DEFAULT 1,
    costo_neto    INTEGER,
    perecible     INTEGER NOT NULL DEFAULT 0,
    dias_aviso    INTEGER
);

-- Migracion ligera para bases creadas con un esquema anterior (sin costo/perecible).
ALTER TABLE productos ADD COLUMN costo_neto INTEGER;
ALTER TABLE productos ADD COLUMN perecible INTEGER NOT NULL DEFAULT 0;
ALTER TABLE productos ADD COLUMN dias_aviso INTEGER;

CREATE TABLE IF NOT EXISTS existencias (
    codigo_producto TEXT PRIMARY KEY,
    cantidad        TEXT NOT NULL DEFAULT '0',
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);

CREATE TABLE IF NOT EXISTS historial_precios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_producto TEXT NOT NULL,
    precio_anterior INTEGER NOT NULL,
    precio_nuevo    INTEGER NOT NULL,
    usuario         TEXT NOT NULL,
    fecha           TEXT NOT NULL,
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);

CREATE TABLE IF NOT EXISTS historial_ajustes_inventario (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_producto    TEXT NOT NULL,
    cantidad_anterior  TEXT NOT NULL,
    cantidad_nueva     TEXT NOT NULL,
    diferencia_conteo  TEXT NOT NULL,
    motivo             TEXT NOT NULL,
    usuario            TEXT NOT NULL,
    fecha              TEXT NOT NULL,
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
    """Crea el esquema; tolera migraciones ya aplicadas (columnas duplicadas)."""
    for sentencia in DDL.strip().split(";"):
        sentencia = sentencia.strip()
        if not sentencia:
            continue
        try:
            conexion.execute(sentencia)
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
