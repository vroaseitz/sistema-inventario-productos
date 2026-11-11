-- Migracion 009 - Cupo de credito por cliente (CL-01, QA del 09-11, definido por la PO)
--
-- Se aplica DESPUES de 002 a 008 sobre el schema `pos` (SET search_path TO pos).
-- Idempotente: se puede ejecutar mas de una vez. No borra ni cambia datos existentes.
--
-- El cupo es lo maximo que un cliente puede deber. NULL = sin cupo definido (no se limita), que
-- es lo que quedan los clientes que ya existen hasta que se les escriba uno. El cupo disponible
-- no se guarda: es cupo - saldo, y pagar (todo o un abono) lo libera.

ALTER TABLE cliente ADD COLUMN IF NOT EXISTS cupo_credito NUMERIC(14, 2)
    CHECK (cupo_credito IS NULL OR cupo_credito >= 0);

-- Mantiene los permisos de pos_app al dia (migracion 005).
SELECT pos.aplicar_permisos_pos_app();
