# Plan de implantación — viernes 20-11-2026

**Versión:** 1.0 · **Fecha:** 19-11-2026 · **Responsables:** Fernando (desarrollo, `.exe`, importador), Victoria (QA,
Supabase, datos), Eduardo (revisión de PR) · Es una **propuesta**: lo marcado «Decidir» necesita acuerdo del equipo.

Se apoya en el ensayo con los datos reales del 18-11 (1.701 productos, 15 clientes, 3.432 operaciones por
sincronizar), el premortem de la implantación y la revisión de código independiente del 19-11.

## Etapa 0 — Congelar y probar (jueves 19-11)

| # | Tarea | Responsable | Listo cuando |
|---|---|---|---|
| 0.1 | **Una sola rama** para QA y para compilar: `fix/qa-18-11` (sale de `fix/qa-16-11`). Nadie más sube cambios | Fernando, Eduardo | Rama congelada; PR `fix/qa-18-11 → develop` abierto |
| 0.2 | **Decidir SY-01:** Eduardo y Fernando lo implementaron por separado; quedarse con una versión | Fernando, Eduardo | Una sola versión en la rama |
| 0.3 | QA manual sobre `fix/qa-18-11` con `docs/11-pruebas/qa-manual-19-11.md` (QM-01 a QM-40; los de internet, en el PC del local) | Victoria | Tabla de resultados llena; fallas en el registro de defectos |
| 0.4 | Aplicar en Supabase las migraciones **009** y **010** (`database/migraciones/`, versiones «pegar en SQL Editor») y correr la consulta de verificación de la 010 | Victoria | La consulta devuelve 0 filas |
| 0.5 | `scripts/verificar_supabase.py` con la `.env` real (la `.env` solo por canal privado) | Victoria | «OK» con las migraciones nuevas |
| 0.6 | Suite completa con PostgreSQL de pruebas (Docker): `POS_TEST_PG_URL=… pytest tests` | Fernando | 542 pruebas pasan y ninguna omitida |
| 0.7 | Revisar los hallazgos del ciclo 8 del registro de defectos y cerrar los que QA apruebe | Victoria | Registro actualizado |

## Etapa 1 — Compilar y ensayar en la VM (jueves 19-11, tarde y noche)

| # | Tarea | Responsable | Listo cuando |
|---|---|---|---|
| 1.1 | Compilar el `.exe` en la VM Windows 8.1 con el commit congelado (`scripts/construir_exe_vm.bat`) | Fernando | `.exe` arranca, entra, vende y cierra la jornada |
| 1.2 | Ensayar el importador en la VM con los CSV **actuales**: primero `--simulacro`, luego carga real en una base de ensayo | Fernando | Resumen sin sorpresas (≈ 1.701 productos y 15 clientes) |
| 1.3 | Primera sincronización de ensayo contra Supabase de **pruebas** (no la real) con el botón «Sincronizar», por tandas | Fernando | Termina; las «rechazadas», si hay, se entienden |
| 1.4 | Probar impresora y cajón si hay equipo (hoy no hay prueba con impresora real) | Victoria | Comprobante e impresión OK, o queda anotado como riesgo |

## Etapa 2 — Corte de datos (viernes 20-11, mañana)

**Regla: la base nueva se carga siempre vacía, con la extracción hecha al cierre del último día del sistema
antiguo.** El importador omite lo que ya existe, así que no sirve para «actualizar» una base con datos.

| # | Tarea | Responsable | Listo cuando |
|---|---|---|---|
| 2.1 | **Decidir el momento del corte:** último cierre del sistema antiguo y desde cuándo se vende solo en el nuevo | Victoria, dueñas | Hora acordada y comunicada |
| 2.2 | Extracción nueva del respaldo (productos y clientes) en ese momento | Victoria | CSV nuevos, entregados por canal privado |
| 2.3 | Importar en una base **vacía** (en la VM) y revisar el resumen; copiar `pos_local.db` y el `.exe` al PC del local. **Decidir** si el importador se empaqueta aparte o se usa siempre desde la VM | Fernando | Base cargada en el PC del local |
| 2.4 | Carga masiva a la nube **antes de abrir**: botón «Sincronizar» con buena conexión (≈ 3.400 operaciones; con 100 ms de latencia simulada, unos 19 minutos). Repetir el botón hasta «Todo sincronizado» | Fernando | Barra en «Todo sincronizado» y 0 rechazadas (o las rechazadas explicadas) |
| 2.5 | Borrar los CSV de clientes de la VM, Descargas y chats; la `.env` solo en el PC del local, fuera del repositorio | Fernando | Verificado por escrito |

## Etapa 3 — Apertura y capacitación (viernes 20-11)

| # | Tarea | Responsable |
|---|---|---|
| 3.1 | Abrir la jornada con el fondo real y hacer una venta de prueba y su anulación (con las tres opciones) | Fernando, Roxana |
| 3.2 | Capacitar a Roxana y Germaine: vender, cobrar, crédito y abono, **anular (las tres opciones)**, corte de caja | Fernando, Victoria |
| 3.3 | Explicar que «Quedan N sin enviar» **no es un error**: se envía solo en el siguiente cierre o con «Sincronizar» | Fernando |
| 3.4 | Explicar el «Revisar» de F2: productos sin costo (39), con precio $0 (25) y «Sin categoría» (491) | Victoria |
| 3.5 | Hoja de una página con las tres opciones al anular y un ejemplo de cierre de caja | Fernando |

## Etapa 4 — Primera semana

- **Copia diaria** de `pos_local.db` al cerrar la jornada (la nube es la segunda copia, no la única).
- **Revisar los 3 primeros cierres** con las dueñas (diferencias de caja, retiros «Devolución»).
- Revisar las operaciones «rechazadas por la nube» (barra de estado de F1): se reintentan solas en cada
  sincronización; si siguen, avisar a soporte.
- Dejar el sistema antiguo disponible solo para consulta durante la primera semana.
- Completar teléfono de los clientes (15 quedaron con «Sin teléfono (migración)») y la lista de revisión de
  Roxana (49 productos sin costo, sin precio o con costo mayor al precio).

## Criterios para decir «sí» el viernes por la mañana

- [ ] QA de Victoria sobre `fix/qa-18-11` sin defectos de prioridad Alta abiertos.
- [ ] Migraciones 009 y 010 aplicadas en Supabase y verificadas con la `.env` real.
- [ ] Suite completa con PostgreSQL en verde y E2E de migración en verde sobre el mismo commit del `.exe`.
- [ ] Corte de datos acordado y extracción hecha ese mismo día.
- [ ] Copia de `pos_local.db` y sistema antiguo disponibles para volver atrás.

Si falta alguno de los dos primeros, **no se corta el sistema antiguo**: se implanta el nuevo en paralelo
(solo consulta) hasta tenerlos.

## Vuelta atrás

1. Dejar de usar el `.exe` y seguir con el sistema antiguo (disponible toda la primera semana).
2. Las ventas hechas en el sistema nuevo están en `pos_local.db` (copia diaria) y, si se sincronizó, en
   Supabase: se pasan a mano al sistema antiguo.
3. Registrar en el registro de defectos qué falló y por qué.

## Riesgos conocidos que no se resuelven antes del viernes

- **Impresora y cajón reales:** sin prueba.
- **IVA e IABA de los productos migrados:** no se separan; el costo neto de los ~138 líquidos ya trae el IABA de
  forma aproximada (definición de la PO). Se afina desde F2.
- **Duplicados (14 pares) y la lista de revisión de Roxana:** se migran todos; se desactivan los que ella diga.
- **Descuento por producto y tasa de IABA:** viven solo en la base local; la copia en Supabase no los tiene
  (haría falta una migración 011 con sus columnas).
- **Anulaciones hechas antes de actualizar** con la jornada abierta: el cierre mostraría un sobrante. Actualizar
  con la jornada cerrada.
