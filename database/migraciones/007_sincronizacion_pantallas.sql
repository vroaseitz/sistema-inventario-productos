-- Migracion 007 - Datos de las pantallas nuevas que ahora viajan a Supabase
--
-- Se aplica DESPUES de 002 a 006 sobre el schema `pos` (SET search_path TO pos).
-- Idempotente: se puede ejecutar mas de una vez.
--
--   * producto.stock_minimo      existencia minima (HU-INV-05). El costo, es_perecible y
--                                dias_aviso_vencimiento ya existen desde 002.
--   * categoria.activa           categorias desactivables (CA-16); desactivar no borra productos.
--   * venta.nota                 nota libre de la venta (F1).
--   * venta_detalle.motivo_descuento  motivo obligatorio del descuento a la linea (F1).
--   * lote.codigo_lote           codigo de lote impreso en el envase (I-02).

ALTER TABLE producto       ADD COLUMN IF NOT EXISTS stock_minimo INTEGER CHECK (stock_minimo >= 0);
ALTER TABLE categoria      ADD COLUMN IF NOT EXISTS activa BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE venta          ADD COLUMN IF NOT EXISTS nota TEXT;
ALTER TABLE venta_detalle  ADD COLUMN IF NOT EXISTS motivo_descuento TEXT;
ALTER TABLE lote           ADD COLUMN IF NOT EXISTS codigo_lote TEXT;

-- Mantiene los permisos de pos_app al dia (migracion 005).
SELECT pos.aplicar_permisos_pos_app();
