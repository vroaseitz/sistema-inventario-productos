-- Migracion 010 - Permitir precio 0 en producto (migracion de datos, QA 18-11)
--
-- 002 creo `producto.precio_venta` con CHECK (precio_venta > 0), pero la base local permite 0
-- (precio >= 0) y el respaldo del sistema antiguo trae 25 productos con precio $0 («sin precio»,
-- pendientes de revision con Roxana). Al sincronizar, Supabase rechazaria esos productos y,
-- como la cola se detiene en el primer fallo, dejaria sin enviar TODO lo que viene detras.
--
-- Se permite 0 en la base de la nube (igual que en el local): el control de «precio faltante»
-- vive en la aplicacion (F2 marca «Revisar» y el resumen del dia avisa).
--
-- Se aplica DESPUES de 002 a 009 sobre el schema `pos` (SET search_path TO pos).
-- Idempotente: se puede ejecutar mas de una vez. No cambia datos.

ALTER TABLE producto DROP CONSTRAINT IF EXISTS producto_precio_venta_check;
ALTER TABLE producto ADD CONSTRAINT producto_precio_venta_check CHECK (precio_venta >= 0);

-- Verificar que no quede otra restriccion que exija precio > 0 (debe devolver 0 filas):
--   SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--   WHERE conrelid = 'pos.producto'::regclass AND pg_get_constraintdef(oid) LIKE '%precio_venta > 0%';
