-- Migracion 008 - Clientes, credito, proveedores, facturas de compra y auditoria viajan a Supabase
--
-- Se aplica DESPUES de 002 a 007 sobre el schema `pos` (SET search_path TO pos).
-- Idempotente: se puede ejecutar mas de una vez. No borra ni cambia datos existentes.
--
-- El modelo remoto (002) es mas chico que el local, asi que se agregan las columnas que faltan
-- y una clave para que reintentar una operacion tras un corte no duplique nada:
--
--   * cliente             id_cliente = «cliente:<id local>»; telefono, correo, observaciones, activo.
--   * movimiento_credito  id_cliente = UUID del movimiento (UNIQUE); medio y detalle. El local
--                         llama «consumo» a lo que aqui es «cargo»; el descuento del credito
--                         familiar (HU-CLI-04) viaja como abono con medio «descuento».
--   * proveedor           nombre unico sin distinguir mayusculas; contacto.
--   * factura_compra      unica por (proveedor, numero); impuestos y estado.
--   * factura_compra_detalle  costo anterior, vencimiento y codigo de lote impreso.
--   * auditoria           id_cliente = «auditoria:<id local>» (UNIQUE); nombre de quien lo hizo
--                         (el usuario remoto es la cuenta tecnica) y el detalle.
--
-- Los usuarios NO viajan: llevarian el hash de las contrasenas a la nube (ver docs/avances).

-- Clientes con credito
ALTER TABLE cliente ADD COLUMN IF NOT EXISTS id_cliente    TEXT;
ALTER TABLE cliente ADD COLUMN IF NOT EXISTS telefono      TEXT    NOT NULL DEFAULT '';
ALTER TABLE cliente ADD COLUMN IF NOT EXISTS correo        TEXT    NOT NULL DEFAULT '';
ALTER TABLE cliente ADD COLUMN IF NOT EXISTS observaciones TEXT    NOT NULL DEFAULT '';
ALTER TABLE cliente ADD COLUMN IF NOT EXISTS activo        BOOLEAN NOT NULL DEFAULT TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS ux_cliente_id_cliente ON cliente (id_cliente);

-- Cuenta del cliente: cargos (consumos) y abonos
ALTER TABLE movimiento_credito ADD COLUMN IF NOT EXISTS id_cliente TEXT;
ALTER TABLE movimiento_credito ADD COLUMN IF NOT EXISTS medio      TEXT;
ALTER TABLE movimiento_credito ADD COLUMN IF NOT EXISTS detalle    TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS ux_movimiento_credito_id_cliente
    ON movimiento_credito (id_cliente);

-- Proveedores
ALTER TABLE proveedor ADD COLUMN IF NOT EXISTS contacto TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS ux_proveedor_nombre ON proveedor (lower(nombre));

-- Facturas de compra
ALTER TABLE factura_compra ADD COLUMN IF NOT EXISTS monto_impuestos NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE factura_compra ADD COLUMN IF NOT EXISTS estado          TEXT NOT NULL DEFAULT 'confirmada';
CREATE UNIQUE INDEX IF NOT EXISTS ux_factura_compra_numero
    ON factura_compra (proveedor_id, numero_factura);

ALTER TABLE factura_compra_detalle ADD COLUMN IF NOT EXISTS costo_anterior    NUMERIC(12, 2);
ALTER TABLE factura_compra_detalle ADD COLUMN IF NOT EXISTS fecha_vencimiento DATE;
ALTER TABLE factura_compra_detalle ADD COLUMN IF NOT EXISTS codigo_lote       TEXT NOT NULL DEFAULT '';

-- Auditoria
ALTER TABLE auditoria ADD COLUMN IF NOT EXISTS id_cliente     TEXT;
ALTER TABLE auditoria ADD COLUMN IF NOT EXISTS usuario_nombre TEXT NOT NULL DEFAULT '';
ALTER TABLE auditoria ADD COLUMN IF NOT EXISTS detalle        TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS ux_auditoria_id_cliente ON auditoria (id_cliente);

-- Mantiene los permisos de pos_app al dia (migracion 005).
SELECT pos.aplicar_permisos_pos_app();
