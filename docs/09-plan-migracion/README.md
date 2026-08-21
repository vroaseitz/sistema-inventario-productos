# 09 · Plan de migración

Estrategia, ensayos y plan de reversa de la migración de datos.

## Qué va aquí

- Plan de migración desde `PDVDATA.FDB` hacia Supabase
- Mapeo de tablas y campos entre ambos sistemas
- Reglas de limpieza, validación y normalización
- **Registro de cada ensayo** realizado en máquina virtual: fecha, resultado, incidencias, correcciones
- **Plan de reversa**: procedimiento para reinstalar el sistema antiguo desde el respaldo
- Checklist del día del corte

## Principio

La migración es un **evento único**. No hay convivencia entre ambos sistemas. El respaldo previo se conserva intacto como garantía de reversa.

> Los ensayos son evidencia del proyecto: cada uno debe quedar documentado.
