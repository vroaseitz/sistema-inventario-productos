# Proceso de migración

Traspaso **único** de los datos desde la base Firebird del sistema antiguo hacia Supabase.

```text
Extract     Lectura de PDVDATA.FDB (copia del respaldo, nunca la base en producción)
   ↓
Transform   Limpieza, validación, normalización y detección de duplicados
   ↓
Load        Carga hacia la nueva base de datos
```

## Reglas

- Se ejecuta **una sola vez**, en el corte de sistema. No es una sincronización permanente.
- Se ensaya varias veces en máquina virtual antes del corte real.
- Cada ensayo se documenta en `docs/09-plan-migracion/`.
- El respaldo previo se conserva intacto como plan de reversa.
