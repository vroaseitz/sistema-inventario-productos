# 11 · Pruebas

Planes de prueba y resultados.

## Qué va aquí

- Plan de pruebas por sprint
- Casos de prueba y criterios de aceptación
- Resultados de la ejecución
- Evidencias: capturas, reportes, registros

## Marco de pruebas (Sprint 2)

- **Framework:** `pytest` (ejecución) + `ruff` (lint/format) — configurados en `pyproject.toml` (`pythonpath=src`, `testpaths=tests`).
- **Gate de calidad**, antes de cualquier commit o PR:
  ```bash
  ruff check .
  ruff format --check .
  pytest
  ```
- **Convención de nombres:** `test_<módulo>.py` dentro de la carpeta que corresponde al tipo de prueba; una función `test_*` por caso, con dobles de prueba (fakes/stubs) en memoria para las unitarias.
- **Criterio de aceptación del sprint:** las pruebas unitarias e integración deben pasar en verde (`pytest` sin fallos) antes de cerrar cualquier tarea de código en ClickUp.

## Tipos de prueba exigidos

| Tipo | Carpeta de código | Casos actuales |
| --- | --- | --- |
| Unitarias | `tests/unitarias/` | 44 (dominio, casos de uso, traductor Supabase) |
| Integración | `tests/integracion/` | 11 (repositorio SQLite, cola de sincronización) |
| Rendimiento | `tests/rendimiento/` | 0 — pendiente, se define en un sprint posterior (requiere volumen de datos real) |
| Seguridad | `tests/seguridad/` | 0 — pendiente, se define junto con los requisitos no funcionales de `docs/04-requisitos-no-funcionales/` |

**Total verificado:** 55 pruebas, todas en verde (`pytest` 55 passed, `ruff check .` sin errores) — verificado el 12 de septiembre de 2026 tras fusionar `develop` a `main`.

## Detalle por archivo (unitarias e integración)

| Archivo | Casos | Qué cubre |
| --- | --- | --- |
| `tests/unitarias/test_codigo_barras.py` | 21 | Parser EAN-13, incluyendo códigos con peso embebido para productos a granel |
| `tests/unitarias/test_productos.py` | 8 | Entidad Producto e Inventario (reglas de dominio) |
| `tests/unitarias/test_casos_uso.py` | 6 | Casos de uso: registrar, escanear, ajustar stock, sincronizar pendientes |
| `tests/unitarias/test_inventario.py` | 5 | Reglas de stock e inventario |
| `tests/unitarias/test_dinero.py` | 4 | Value object Dinero, política de redondeo HALF_UP |
| `tests/unitarias/test_traductor_supabase.py` | 4 | Traducción de operaciones locales a SQL para el adaptador Supabase |
| `tests/integracion/test_repositorio_sqlite.py` | 4 | Repositorios SQLite (productos, existencias) contra base real |
| `tests/integracion/test_cola_sincronizacion.py` | 3 | Cola de sincronización offline→Supabase, orden estricto por rowid |

## Pendiente

- [ ] Definir plan de pruebas de **rendimiento** (tiempos de respuesta en caja) una vez cerrados los requisitos no funcionales.
- [ ] Definir plan de pruebas de **seguridad** (control de acceso, resguardo de credenciales) junto con `docs/04-requisitos-no-funcionales/`.
- [ ] Revisión del equipo completo de este marco de pruebas (Victoria, Eduardo) antes de cerrar la tarea en ClickUp — el detalle técnico lo aportó Fernando desde el código ya escrito, pero el marco debe quedar validado por todo el equipo.

> **Responde al instructivo:** pruebas (obligatorio transversal) y plan de pruebas por sprint.
