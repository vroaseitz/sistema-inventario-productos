# Plan de migración de datos (Firebird → Supabase)

## Principio: la migración está DESACOPLADA de la aplicación

La app de escritorio **no** incluye ningún driver de Firebird. La migración es un
**proceso único**, separado, que se ejecuta una sola vez en el corte del sistema.

## Por qué desacoplada (hallazgo del premortem)

El sistema antiguo (**Abarrotes PDV 2.12**) usa **Firebird 2.x embebido** (archivo
`PDVDATA.FDB`), edición MonoCaja. Ese motor y su `fbclient.dll`/`fbembed.dll` son casi
con seguridad de **32 bits**. Un Python de 64 bits **no puede cargar una DLL de 32
bits** (`WindowsError [193]: %1 is not a valid Win32 application`). Si la app llevara el
driver, ataría todo el sistema a ese problema de arquitectura.

## Procedimiento recomendado (menor riesgo)

1. **Respaldar primero.** Copiar el `PDVDATA.FDB` y trabajar SIEMPRE sobre la copia,
   nunca sobre el archivo del local en producción.
2. **Exportar con herramientas nativas de Firebird 2.5** (no con un driver Python):
   - `gbak` para un respaldo íntegro, o
   - `isql` con `OUTPUT archivo.csv;` + `SELECT ...` para volcar cada tabla a CSV.
   Esto se hace con las herramientas de Firebird 2.5 de **32 bits**, que sí abren el
   `.FDB` embebido.
3. **Depurar** el catálogo: de ~4.100 registros, solo ~600 están activos; el resto es
   basura histórica del dueño anterior. La limpieza se documenta y se versiona.
4. **Cargar** los datos limpios a Supabase (y/o al espejo SQLite) con un importador
   CSV → base. Ese importador sí es Python y es testeable con CSV de ejemplo.

## Alternativa (si se requiere leer el FDB desde Python)

Usar un **Python 3.11 de 32 bits** + el paquete `fdb` + `fbclient.dll` de **Firebird
2.5 de 32 bits**, en un entorno aislado dedicado solo a la migración. `firebird-driver`
NO sirve: es para Firebird 3+.

## Plan de reversa

El respaldo previo (`gbak`) se conserva intacto. Si en los primeros días algo falla,
se reinstala el sistema antiguo desde ese respaldo. **El plan de reversa se prueba
(restore real), no solo se declara.**

## Pendiente (requiere entorno real / acción de Fernando)

- [ ] Conseguir copia del `PDVDATA.FDB` del local.
- [ ] Instalar herramientas Firebird 2.5 (32-bit) y exportar las tablas a CSV.
- [ ] Escribir el importador CSV → SQLite/Supabase con sus pruebas.
- [ ] Ensayar la migración completa en máquina virtual y registrar la evidencia.
