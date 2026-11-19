-- Migracion 003 - Retirar el CHECK que impide vender bajo el costo (HU-INV-06)
--
-- 002_modelo_completo.sql agrego `producto_no_vende_bajo_costo` para blindar el
-- defecto de dato detectado en el analisis legado (9 fichas con precio bajo el
-- costo, la mayoria coma corrida en el campo de costo). Pero el Product Backlog
-- v4.3 precisa HU-INV-06: de esas 9 fichas, 5 son liquidaciones REALES (producto
-- proximo a vencer, vendido bajo costo a proposito) y 4 son errores de dato. Un
-- CHECK a nivel de base de datos no puede distinguir una liquidacion legitima de
-- un error de tipeo, asi que bloquearia exactamente los 5 casos que el negocio
-- necesita poder hacer.
--
-- El control se traslada al formulario de la aplicacion (advertencia, no bloqueo):
-- la UI avisa cuando el precio ingresado queda bajo el costo cargado, pero deja
-- confirmar y guardar. La exigencia de una liquidacion real es que quede
-- registrada como tal (motivo explicito), no que la base de datos la rechace.
--
-- Ejecutar contra el proyecto de Supabase a traves del pooler (ver docs/08-diseno/adr/0001)
-- despues de 002_modelo_completo.sql.

ALTER TABLE producto DROP CONSTRAINT IF EXISTS producto_no_vende_bajo_costo;
