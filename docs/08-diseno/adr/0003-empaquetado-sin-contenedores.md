# ADR 0003 — Distribución sin contenedores (PyInstaller)

- **Estado:** Aceptado
- **Fecha:** 2026-08-24
- **Decisores:** Equipo Capstone (Fernando Silva — desarrollo)

## Contexto

Se evaluó usar **Docker** para "que corra en cualquier PC", pero se descartó. Razones:

- El objetivo real es una **aplicación de escritorio** que corre en el **PC del local
  (Windows 8.1)**. Docker Desktop **no soporta Windows 8.1** (requiere Windows 10/11 con
  WSL2/Hyper-V), así que en el equipo destino no es viable.
- El informe de Definición del proyecto declara "**sin contenedores**", y la profesora
  guía **eximió al equipo de contenerización** porque el sistema no ejecuta nada como
  servicio propio (la base de datos es gestionada por un tercero: Supabase).

Introducir Docker reabriría esa discusión sin aportar valor al escenario real.

## Decisión

**No se usan contenedores.** La aplicación se distribuye como **ejecutable empaquetado
con PyInstaller** (ver `build/pos.spec`), instalable en el PC del local. La base de datos
en la nube la provee **Supabase** (servicio gestionado).

## Portabilidad como requisito no funcional (mecanismos equivalentes)

En lugar de contenedores, la portabilidad y reproducibilidad se cubren con:

| Mecanismo | Ubicación |
|---|---|
| Manual técnico de despliegue | `docs/12-despliegue/` (pendiente) |
| Ejecutable/instalador empaquetado | `build/pos.spec` → `dist/` |
| Variables de entorno separadas del código | `config/.env.example` (+ `.env` en `.gitignore`) |
| Dependencias fijadas | `requirements.txt` / `requirements-dev.txt` |
| Esquema de datos versionado | `database/migraciones/` |

## Consecuencia importante (acción para el equipo)

> El README principal y el informe dicen "sin contenedores". Esta decisión **lo confirma**
> (no lo contradice). Como en algún momento se conversó usar Docker, **Fernando debe
> avisar/ratificar con la profesora Karla Roco** que la distribución final es por
> instalador PyInstaller, para mantener la coherencia con la exención ya otorgada. No se
> requiere cambio en el informe salvo dejar explícito el empaquetado.

## Nota sobre el build (ver ADR 0001)

El `.exe` **hereda la compatibilidad de la máquina donde se construye**. Para que corra en
Windows 8.1 hay que **compilar en una VM Windows 8.1** (o Win 7) con Python 3.11 64-bit.
Compilar en Windows 10/11 genera un binario que no arranca en el 8.1.
