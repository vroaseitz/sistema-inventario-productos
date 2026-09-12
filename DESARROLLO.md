# Guía de desarrollo — Sistema POS NaturalSur

Aplicación de escritorio (Python) para el punto de venta e inventario del Emporio
NaturalSur. Este documento explica cómo levantar el entorno, correr las pruebas y
empaquetar. Las decisiones técnicas y su justificación están en
[`docs/08-diseno/adr/`](docs/08-diseno/adr/README.md).

## Stack (resumen — ver ADR 0001)

- **Python 3.11 (64-bit)** — última versión de CPython que soporta el Windows 8.1 del local.
- **Tkinter** para la GUI (incluido en CPython, sin dependencias externas).
- **SQLite** como espejo local (operación offline).
- **Supabase (PostgreSQL)** en la nube, vía `psycopg2` por el **pooler**.
- **pytest** (pruebas) + **ruff** (lint/format). Empaquetado con **PyInstaller**.

## Estructura (arquitectura por capas — SOLID)

```
src/pos/
  dominio/          # Lógica pura: entidades, value objects, parser EAN-13. Sin dependencias.
  aplicacion/       # Casos de uso + puertos (interfaces). Dependen de abstracciones, no de infra.
    casos_uso/
  infraestructura/  # Implementaciones concretas de los puertos.
    sqlite/         # Espejo local + cola de sincronización.
    supabase/       # Adaptador de publicación remota (requiere credenciales).
  interfaz/         # GUI Tkinter (desacoplada; consume casos de uso).
  __main__.py       # Raíz de composición: arma dependencias e inicia la app.
tests/
  unitarias/        # Dominio y casos de uso (con dobles en memoria).
  integracion/      # Repositorios y cola contra SQLite real.
database/migraciones/  # DDL de PostgreSQL/Supabase.
build/pos.spec         # Empaquetado PyInstaller (compilar en VM Win 8.1).
```

El flujo de dependencias apunta **hacia adentro**: `interfaz → aplicacion → dominio`, y la
`infraestructura` implementa los puertos de `aplicacion` (Inversión de Dependencias).

## Puesta en marcha

> Para desarrollar sirve cualquier Python reciente; para el **build final** hacia el local
> se usa **Python 3.11** en una **VM Windows 8.1** (ver ADR 0001 y 0003).

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements-dev.txt

cp config/.env.example .env   # completar credenciales de Supabase (NO se versiona)
```

## Correr las pruebas (gate de calidad)

```bash
ruff check .          # lint
ruff format --check . # formato
pytest                # pruebas (unitarias + integración)
```

`pyproject.toml` ya configura `pythonpath=src`, así que `pytest` encuentra el paquete `pos`.

## Ejecutar la app

```bash
python -m pos
```

## Empaquetar (instalador para el local)

```bash
# Dentro de una VM Windows 8.1 con Python 3.11 (ver ADR 0003):
pip install pyinstaller
pyinstaller build/pos.spec   # genera dist/pos-naturalsur/
```

## Qué requiere entorno real (no cubierto aún)

- Credenciales de Supabase para probar la sincronización de extremo a extremo.
- Copia del `PDVDATA.FDB` del local y herramientas Firebird 2.5 (32-bit) para la migración
  (ver `docs/09-plan-migracion/`).
- Una VM Windows 8.1 para la prueba de humo del `.exe`.
