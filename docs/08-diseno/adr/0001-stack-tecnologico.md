# ADR 0001 — Stack tecnológico de la aplicación de escritorio

- **Estado:** Aceptado
- **Fecha:** 2026-08-24
- **Decisores:** Equipo Capstone (Fernando Silva — desarrollo)

## Contexto

La aplicación reemplaza el software legacy del Emporio NaturalSur. Restricciones reales
que condicionan la decisión (no son preferencias):

1. **Debe ejecutarse en el PC del local, que corre Windows 8.1 64-bit.** Es la
   restricción dura #1. El hardware es antiguo y no se va a actualizar en el marco del
   proyecto.
2. Debe ser **aplicación de escritorio**, no una página web (requisito de la asignatura).
3. Debe **conectarse a Supabase (PostgreSQL)** en la nube.
4. Debe **funcionar sin conexión a internet** (hoy el local vende offline; no puede haber
   regresión — ver ADR 0002).
5. Debe **empaquetarse como instalador/ejecutable** para el equipo del local.
6. El framework de pruebas debe ser compatible con el stack.

## Opciones evaluadas

| Opción | ¿Corre en Win 8.1? | Notas |
|---|---|---|
| **Python 3.11 + Tkinter + PyInstaller** | **Sí** | Python 3.11 es la última versión de CPython que soporta Win 8.1. Tkinter viene incluido, sin dependencias externas ni runtime extra. |
| Python + PyQt5 (Qt5) | Sí, con reparos | Qt5 soporta Win 8.1, pero los wheels recientes requieren el runtime Visual C++ redistribuible presente en el local; hay que empaquetarlo. |
| Python 3.12+ | **No** | 3.12 subió el mínimo a Windows 10 (PEP 11). Compilaría en una máquina moderna y **moriría en el 8.1**. |
| Electron (moderno) | **No** | Electron 23+ eliminó el soporte de Windows 7/8/8.1. El último compatible (Electron 22) usa Chromium 108, ya inseguro. |
| Tauri | **No** | Depende de WebView2, que en Win 8.1 quedó limitado a la v109 y sin soporte. |
| .NET 7/8 (WPF) | **No** | .NET moderno no soporta Win 8.1. .NET 6 sí, pero está en fin de vida. Además el equipo descartó .NET. |

## Decisión

**Python 3.11 (64-bit) + Tkinter para la GUI + PyInstaller para el empaquetado.**
Conexión a Supabase mediante **psycopg2-binary** a través del **pooler** de Supabase.

### Justificación por requerimientos

- **(R1) Windows 8.1:** Python 3.11 es la última versión soportada; Tkinter va incluido
  y es el toolkit de menor riesgo en 8.1 (cero dependencias externas). Se fija 3.11 de
  forma estricta (`requires-python = ">=3.11,<3.12"`).
- **(R3/R4) Supabase + TLS:** los wheels de `psycopg2-binary` traen su **propio libpq y
  OpenSSL**, por lo que la negociación **TLS 1.2 no depende del SChannel de Windows 8.1**.
  Esta es la ventaja decisiva de Python frente a .NET/Electron, que usan el TLS del SO:
  en un Windows viejo y sin parches, esos stacks pueden fallar el handshake con Supabase;
  Python no.
- **(R5) Empaquetado:** PyInstaller genera el ejecutable. **Debe construirse en una VM
  Windows 8.1** (o Win 7) para que el binario no enlace DLLs ausentes en el destino
  (ver ADR 0003 y `build/pos.spec`).
- **(R6) Pruebas:** `pytest`, compatible y estándar en Python. Lint/format con `ruff`.

### Descartes explícitos

- **Electron y Tauri:** quedan fuera por incompatibilidad con Windows 8.1 (Electron 23+
  y WebView2 dejaron de soportarlo).
- **.NET 7/8:** no soporta Windows 8.1; además fue descartado por decisión del equipo.
- **Python 3.12+:** prohibido para este proyecto; rompe la restricción #1.

## Consecuencias

- **Positivas:** stack accesible para el equipo, sin costo de licencias, TLS robusto en
  hardware viejo, pruebas simples, ejecutable autocontenido.
- **Negativas / a gestionar:**
  - Se necesita una **VM Windows 8.1 como máquina de build** y de prueba de humo. Ningún
    `.exe` se considera terminado hasta que arranca en esa VM.
  - Tkinter da una UI más sobria que Qt; se compensa con `ttk` y buen layout.
  - Hay que fijar el host de Supabase al **pooler** (no al `:5432` directo, deprecado
    para IPv4).

## Fuentes

- CPython issue #98383 — Python 3.12 soporta Windows 10+, no 8.1.
- PEP 11 — política de soporte de plataformas de CPython.
- Electron 23.0.0 release notes — fin de soporte de Windows 7/8/8.1.
- Documentación de instalación de Psycopg — wheels con libpq + OpenSSL propios.
- Supabase Docs — conexión vía pooler / psql.
