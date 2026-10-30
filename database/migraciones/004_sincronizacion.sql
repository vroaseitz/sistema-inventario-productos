-- Migracion 004 - Soporte de sincronizacion offline -> Supabase (ADR 0002)
--
-- Se aplica DESPUES de 002 (y 003) sobre el schema `pos`:
--     SET search_path TO pos;   -- o ejecutar dentro de una transaccion con SET LOCAL
--
-- La app vende contra SQLite local y publica las operaciones pendientes aqui. Cada
-- operacion lleva un identificador de cliente (UUID) que se guarda en la fila remota,
-- para que reintentar una publicacion NO duplique nada (ON CONFLICT (id_cliente)).
--
-- Los ids numericos locales (SQLite) y remotos (IDENTITY) son independientes; por eso
-- el enlace entre ambos mundos es el UUID (turno, venta) o el codigo interno (producto).

ALTER TABLE producto    ADD COLUMN IF NOT EXISTS codigo     TEXT;
ALTER TABLE turno_caja  ADD COLUMN IF NOT EXISTS id_cliente TEXT;
ALTER TABLE venta       ADD COLUMN IF NOT EXISTS id_cliente TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS producto_codigo_unico    ON producto (codigo);
CREATE UNIQUE INDEX IF NOT EXISTS turno_caja_id_cliente_un ON turno_caja (id_cliente);
CREATE UNIQUE INDEX IF NOT EXISTS venta_id_cliente_un      ON venta (id_cliente);

-- Retiros e ingresos de caja (HU-CAJ-04): el arqueo remoto los necesita.
CREATE TABLE IF NOT EXISTS movimiento_caja (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente     TEXT NOT NULL UNIQUE,
    turno_caja_id  INTEGER NOT NULL REFERENCES turno_caja (id),
    tipo           TEXT NOT NULL CHECK (tipo IN ('retiro', 'ingreso')),
    monto          NUMERIC(12, 2) NOT NULL CHECK (monto > 0),
    motivo         TEXT NOT NULL,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Datos minimos para que las filas sincronizadas cumplan las claves foraneas mientras
-- no exista inicio de sesion (HU de autenticacion) ni catalogo de categorias sincronizado.
-- El hash NO es una contrasena valida: la cuenta no puede iniciar sesion.
INSERT INTO categoria (nombre) VALUES ('Sin categoria') ON CONFLICT (nombre) DO NOTHING;
INSERT INTO usuario (nombre, correo, contrasena_hash)
VALUES ('Caja (sin login)', 'caja@naturalsur.local', '!SIN-LOGIN!')
ON CONFLICT (correo) DO NOTHING;
