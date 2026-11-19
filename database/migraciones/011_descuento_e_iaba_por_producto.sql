-- Migracion 011 - Descuento por vencimiento e IABA por producto (O-42, CA-21)
--
-- Hasta hoy estos datos vivian solo en la base local: al restaurar desde Supabase (la copia fuera
-- del local) se perdian. Se agregan al producto de la nube.
--
-- Se aplica DESPUES de 002 a 010 sobre el schema `pos` (SET search_path TO pos).
-- Idempotente: se puede ejecutar mas de una vez. No borra ni cambia datos existentes.
--
-- * desc_dias_1 / desc_pct_1 / desc_dias_2 / desc_pct_2: etapas del descuento por vencimiento
--   propias del producto (O-42). NULL = rige la politica por defecto. Los rangos los valida la
--   aplicacion, igual que en la base local.
-- * iaba_pct: tasa del impuesto adicional a bebidas, 10 o 18 (CA-21). NULL = no esta afecto.

ALTER TABLE producto ADD COLUMN IF NOT EXISTS desc_dias_1 INTEGER;
ALTER TABLE producto ADD COLUMN IF NOT EXISTS desc_pct_1 INTEGER;
ALTER TABLE producto ADD COLUMN IF NOT EXISTS desc_dias_2 INTEGER;
ALTER TABLE producto ADD COLUMN IF NOT EXISTS desc_pct_2 INTEGER;
ALTER TABLE producto ADD COLUMN IF NOT EXISTS iaba_pct INTEGER
    CHECK (iaba_pct IS NULL OR iaba_pct IN (10, 18));

-- Mantiene los permisos de pos_app al dia (migracion 005).
SELECT pos.aplicar_permisos_pos_app();
