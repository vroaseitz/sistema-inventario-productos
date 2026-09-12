-- Migracion 001 - Esquema inicial (PostgreSQL / Supabase)
-- Equivalente en la nube del espejo local SQLite (src/pos/infraestructura/sqlite/esquema.py).
-- Ejecutar contra el proyecto de Supabase a traves del pooler (ver docs/08-diseno/adr/0001).

CREATE TABLE IF NOT EXISTS productos (
    codigo        TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    precio        INTEGER NOT NULL CHECK (precio >= 0),
    unidad_venta  TEXT NOT NULL DEFAULT 'unidad'
                  CHECK (unidad_venta IN ('unidad', 'granel')),
    categoria     TEXT,
    activo        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS existencias (
    codigo_producto TEXT PRIMARY KEY REFERENCES productos (codigo),
    cantidad        NUMERIC(12, 3) NOT NULL DEFAULT 0 CHECK (cantidad >= 0)
);

-- Espejo de la cola de sincronizacion. id_cliente (UUID generado en el cliente)
-- garantiza idempotencia: reintentar una operacion no la duplica.
CREATE TABLE IF NOT EXISTS cola_sincronizacion (
    id_cliente TEXT PRIMARY KEY,
    entidad    TEXT NOT NULL,
    operacion  TEXT NOT NULL,
    datos      JSONB NOT NULL,
    creado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);
