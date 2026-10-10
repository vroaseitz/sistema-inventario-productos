-- Migracion 002 - Modelo de datos completo (PostgreSQL / Supabase)
--
-- Traduce 1 a 1 el diagrama entidad-relacion de docs/06-modelo-datos/README.md
-- (20 tablas, construido a partir de las 9 correcciones del informe de analisis
-- de la base legada y de las 44 historias de usuario del Product Backlog).
--
-- IMPORTANTE: esta migracion SUPERA a 001_esquema_inicial.sql en las tablas que
-- se repiten (productos, existencias): 001 es un borrador de 3 tablas, anterior
-- a todo el trabajo de ER (categoria como texto, sin desglose de costo). Antes
-- de ejecutar esta migracion en un proyecto que ya corrio 001, hay que decidir
-- si se parte de una base nueva o se migran los datos de 001 -- no se asume
-- ninguna de las dos aca.
--
-- Ejecutar contra el proyecto de Supabase a traves del pooler (ver docs/08-diseno/adr/0001).

-- ============================================================================
-- 1. Catalogos sin dependencias
-- ============================================================================

CREATE TABLE IF NOT EXISTS categoria (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS atributo_dietario (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS usuario (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre            TEXT NOT NULL,
    correo            TEXT NOT NULL UNIQUE,
    contrasena_hash   TEXT NOT NULL,
    activo            BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS motivo_movimiento (
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre               TEXT NOT NULL,
    requiere_comentario  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS cliente (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre         TEXT NOT NULL,
    rut            TEXT,
    tiene_credito  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS proveedor (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre  TEXT NOT NULL,
    rut     TEXT
);

-- ============================================================================
-- 2. Producto y lo que depende de un producto
-- ============================================================================

CREATE TABLE IF NOT EXISTS producto (
    id                          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre                      TEXT NOT NULL,
    categoria_id                INTEGER NOT NULL REFERENCES categoria (id),
    unidad_venta                TEXT NOT NULL CHECK (unidad_venta IN ('UNIDAD', 'GRANEL')),
    precio_venta                NUMERIC(12, 2) NOT NULL CHECK (precio_venta > 0),
    costo_neto                  NUMERIC(12, 2),
    costo_iva                   NUMERIC(12, 2),
    costo_impuesto_adicional    NUMERIC(12, 2),
    costo_total                 NUMERIC(12, 2)
        GENERATED ALWAYS AS (
            COALESCE(costo_neto, 0) + COALESCE(costo_iva, 0) + COALESCE(costo_impuesto_adicional, 0)
        ) STORED,
    costo_cargado                BOOLEAN NOT NULL DEFAULT FALSE,
    es_perecible                 BOOLEAN NOT NULL DEFAULT FALSE,
    dias_aviso_vencimiento       INTEGER,
    activo                       BOOLEAN NOT NULL DEFAULT TRUE,
    creado_por                   INTEGER REFERENCES usuario (id),
    creado_en                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Costo cargado implica que el precio nunca quede bajo el costo total por error
    -- de dato (9 casos detectados en el analisis legado); las liquidaciones reales
    -- quedan fuera de este check y se manejan como excepcion explicita (HU-INV-06).
    CONSTRAINT producto_no_vende_bajo_costo
        CHECK (NOT costo_cargado OR precio_venta >= costo_total)
);

CREATE TABLE IF NOT EXISTS producto_atributo_dietario (
    producto_id            INTEGER NOT NULL REFERENCES producto (id),
    atributo_dietario_id   INTEGER NOT NULL REFERENCES atributo_dietario (id),
    PRIMARY KEY (producto_id, atributo_dietario_id)
);

CREATE TABLE IF NOT EXISTS codigo_barra (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id   INTEGER NOT NULL REFERENCES producto (id),
    codigo        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS lote (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id         INTEGER NOT NULL REFERENCES producto (id),
    fecha_vencimiento   DATE NOT NULL,
    saldo               NUMERIC(12, 3) NOT NULL CHECK (saldo >= 0)
);

CREATE TABLE IF NOT EXISTS existencia (
    producto_id   INTEGER PRIMARY KEY REFERENCES producto (id),
    cantidad      NUMERIC(12, 3) NOT NULL DEFAULT 0 CHECK (cantidad >= 0)
);

CREATE TABLE IF NOT EXISTS movimiento_inventario (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id    INTEGER NOT NULL REFERENCES producto (id),
    tipo           TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida', 'ajuste', 'devolucion')),
    cantidad       NUMERIC(12, 3) NOT NULL,
    -- Motivo obligatorio (HU-INV-04): corrige los 29.715 ajustes de inventario
    -- sin causa registrada en el sistema legado.
    motivo_id      INTEGER NOT NULL REFERENCES motivo_movimiento (id),
    comentario     TEXT,
    usuario_id     INTEGER REFERENCES usuario (id),
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 3. Caja, ventas y credito de cliente
-- ============================================================================

CREATE TABLE IF NOT EXISTS turno_caja (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuario (id),
    fondo_inicial   NUMERIC(12, 2) NOT NULL,
    abierto_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    cerrado_en      TIMESTAMPTZ
);

-- Impide dos turnos de caja abiertos a la vez.
CREATE UNIQUE INDEX IF NOT EXISTS turno_caja_unico_abierto
    ON turno_caja (usuario_id)
    WHERE cerrado_en IS NULL;

CREATE TABLE IF NOT EXISTS venta (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    turno_caja_id       INTEGER NOT NULL REFERENCES turno_caja (id),
    cliente_id          INTEGER REFERENCES cliente (id),
    usuario_id          INTEGER NOT NULL REFERENCES usuario (id),
    estado              TEXT NOT NULL DEFAULT 'pagada' CHECK (estado IN ('pagada', 'anulada')),
    motivo_anulacion    TEXT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Anulaciones sin motivo ni autor: 2.781 casos detectados en el sistema legado.
    CONSTRAINT venta_anulada_requiere_motivo
        CHECK (estado <> 'anulada' OR motivo_anulacion IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS venta_detalle (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    venta_id          INTEGER NOT NULL REFERENCES venta (id),
    producto_id       INTEGER NOT NULL REFERENCES producto (id),
    cantidad          NUMERIC(12, 3) NOT NULL CHECK (cantidad > 0),
    precio_unitario   NUMERIC(12, 2) NOT NULL,
    -- Instantanea del costo neto al momento de la venta: hoy no existe costo
    -- historico, calcular el margen de una venta pasada usa el costo de hoy.
    costo_unitario    NUMERIC(12, 2),
    descuento_linea   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    -- Generada, no escrita: el defecto central del sistema legado (guardar el
    -- margen de la unidad completa en vez del vendido, hasta 148,3% de ganancia
    -- declarada en productos a granel) es imposible de reproducir si la
    -- ganancia se deriva en vez de guardarse.
    ganancia          NUMERIC(14, 2)
        GENERATED ALWAYS AS (
            cantidad * (precio_unitario - COALESCE(costo_unitario, 0)) - descuento_linea
        ) STORED
);

CREATE TABLE IF NOT EXISTS venta_pago (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    venta_id    INTEGER NOT NULL REFERENCES venta (id),
    -- 'tarjeta' sin separar debito/credito: el terminal TUU solo pide
    -- seleccionar "tarjeta" al cobrar, no distingue debito de credito.
    medio_pago  TEXT NOT NULL CHECK (medio_pago IN ('efectivo', 'tarjeta', 'transferencia', 'credito_cliente')),
    monto       NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS movimiento_credito (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id  INTEGER NOT NULL REFERENCES cliente (id),
    -- NULL si es un abono suelto, sin venta asociada.
    venta_id    INTEGER REFERENCES venta (id),
    tipo        TEXT NOT NULL CHECK (tipo IN ('cargo', 'abono')),
    monto       NUMERIC(12, 2) NOT NULL,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 4. Auditoria
-- ============================================================================

CREATE TABLE IF NOT EXISTS auditoria (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tabla           TEXT NOT NULL,
    registro_id     TEXT NOT NULL,
    usuario_id      INTEGER REFERENCES usuario (id),
    accion          TEXT NOT NULL,
    datos_antes     JSONB,
    datos_despues   JSONB,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 5. Compras a proveedor
-- ============================================================================

CREATE TABLE IF NOT EXISTS factura_compra (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proveedor_id     INTEGER NOT NULL REFERENCES proveedor (id),
    numero_factura   TEXT NOT NULL,
    fecha            DATE NOT NULL,
    monto_neto       NUMERIC(14, 2) NOT NULL,
    usuario_id       INTEGER REFERENCES usuario (id)
);

CREATE TABLE IF NOT EXISTS factura_compra_detalle (
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    factura_id           INTEGER NOT NULL REFERENCES factura_compra (id),
    producto_id          INTEGER NOT NULL REFERENCES producto (id),
    cantidad             NUMERIC(12, 3) NOT NULL,
    costo_unitario_neto  NUMERIC(12, 2) NOT NULL,
    -- NULL si el producto no es perecible.
    lote_id              INTEGER REFERENCES lote (id)
);

-- ============================================================================
-- 6. Indices de apoyo a consultas frecuentes (no son restricciones de integridad)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_producto_categoria ON producto (categoria_id);
CREATE INDEX IF NOT EXISTS idx_movimiento_inventario_producto ON movimiento_inventario (producto_id);
CREATE INDEX IF NOT EXISTS idx_venta_detalle_venta ON venta_detalle (venta_id);
CREATE INDEX IF NOT EXISTS idx_venta_cliente ON venta (cliente_id);
CREATE INDEX IF NOT EXISTS idx_movimiento_credito_cliente ON movimiento_credito (cliente_id);
