-- Migracion 006 - Lotes sincronizables (HU-INV-02 / HU-INV-03 / HU-INV-06)
--
-- `pos.lote` ya existe desde 002 (producto_id, fecha_vencimiento, saldo). El POS crea y
-- consume lotes offline (FEFO) y publica cada cambio de saldo: el UUID local se guarda como
-- id_cliente para que reintentar no duplique (ON CONFLICT (id_cliente) DO UPDATE).
-- Ejecutar con: SET search_path TO pos;

ALTER TABLE lote ADD COLUMN IF NOT EXISTS id_cliente TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS lote_id_cliente_un ON lote (id_cliente);

-- Mantiene los permisos de pos_app al dia (migracion 005).
SELECT pos.aplicar_permisos_pos_app();
