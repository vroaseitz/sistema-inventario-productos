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
    categoria_id  INTEGER,
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

-- Jornada de caja (HU-CAJ-01). El indice unico sobre cerrado_en IS NULL impide
-- dos turnos abiertos a la vez, igual que en database/migraciones/ (Postgres).
CREATE TABLE IF NOT EXISTS turnos_caja (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id         INTEGER NOT NULL,
    fondo_inicial      INTEGER NOT NULL CHECK (fondo_inicial >= 0),
    composicion_fondo  TEXT,
    abierto_en         TEXT NOT NULL DEFAULT (datetime('now')),
    cerrado_en         TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_un_solo_turno_abierto
    ON turnos_caja (cerrado_en) WHERE cerrado_en IS NULL;

-- Movimientos de caja que no son una venta: retiros e ingresos (HU-CAJ-04).
CREATE TABLE IF NOT EXISTS movimientos_caja (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    turno_id   INTEGER NOT NULL,
    tipo       TEXT NOT NULL CHECK (tipo IN ('retiro', 'ingreso')),
    monto      INTEGER NOT NULL CHECK (monto > 0),
    motivo     TEXT NOT NULL,
    creado_en  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (turno_id) REFERENCES turnos_caja(id)
);

CREATE TABLE IF NOT EXISTS ventas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    turno_caja_id  INTEGER NOT NULL,
    usuario_id     INTEGER NOT NULL,
    cliente_id     INTEGER,
    estado         TEXT NOT NULL DEFAULT 'pagada' CHECK (estado IN ('pagada', 'anulada')),
    creado_en      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (turno_caja_id) REFERENCES turnos_caja(id)
);

CREATE TABLE IF NOT EXISTS venta_detalles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id         INTEGER NOT NULL,
    producto_codigo  TEXT NOT NULL,
    cantidad         TEXT NOT NULL,
    precio_unitario  INTEGER NOT NULL,
    costo_unitario   INTEGER,
    descuento_linea  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (venta_id) REFERENCES ventas(id)
);

-- medio_pago admite los cuatro de HU-VTA-03; una venta con pago combinado tiene
-- mas de una fila. monto_entregado/composicion_entregada solo se llenan en efectivo.
CREATE TABLE IF NOT EXISTS venta_pagos (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id               INTEGER NOT NULL,
    medio_pago             TEXT NOT NULL
        CHECK (medio_pago IN ('efectivo', 'tarjeta', 'transferencia', 'credito_cliente')),
    monto                  INTEGER NOT NULL,
    monto_entregado        INTEGER,
    composicion_entregada  TEXT,
    FOREIGN KEY (venta_id) REFERENCES ventas(id)
);
"""


def crear_esquema(conexion: sqlite3.Connection) -> None:
    conexion.executescript(DDL)
