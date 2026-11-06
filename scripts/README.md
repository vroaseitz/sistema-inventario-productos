# Scripts de apoyo
Utilidades de automatización del equipo: carga de datos de prueba, respaldos, tareas repetitivas.

No confundir con `database/scripts/` (consultas SQL) ni con `src/migracion/` (proceso de migración).

## Supabase

| Script | Qué hace | Escribe en la base |
| --- | --- | --- |
| `verificar_supabase.py` | Compara el schema `pos` real con las migraciones 001 a 007: tablas y columnas que faltan o sobran, y filas por tabla. Sale con 1 si falta algo (p. ej. la 007) | No (sesión de solo lectura) |
| `prueba_supabase_real.py` | Prueba de humo de la sincronización con datos `ZZTEST` que borra al terminar | Sí, y lo limpia |

Ambos leen `SUPABASE_DB_URL` del `.env` (plantilla en `config/.env.example`). Con el rol `pos_app` basta
para `verificar_supabase.py`; para pegar migraciones hace falta el rol dueño (`postgres`) en el SQL Editor.
