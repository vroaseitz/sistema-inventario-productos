# 08 · Documento de diseño

Decisiones técnicas del proyecto y su justificación. El detalle completo de cada
decisión vive en su propio ADR (`docs/08-diseno/adr/`); este documento consolida las
cuatro decisiones de diseño y deja explícito qué está resuelto por el equipo y qué sigue
abierto.

## Qué va aquí

- Documento de diseño de la solución
- Justificación de cada decisión técnica: por qué se eligió y qué alternativas se descartaron
- **Sección justificatoria de la excepción de contenedores**, autorizada por la profesora guía el 21-08-2026
- Decisión sobre productos pesables y el parser de códigos de barras con peso embebido (prefijos 20-29)

## Decisiones registradas

| Decisión | Estado | Detalle |
| --- | --- | --- |
| Alcance: punto de venta completo | Resuelta | Reemplaza el sistema legado completo, no solo gestión de productos (decisión de equipo, ClickUp "Decisiones pendientes") |
| Migración como evento único, sin convivencia | Resuelta | `docs/09-plan-migracion/README.md` |
| Stack de la aplicación de escritorio | Resuelta — 24-08-2026 | [ADR 0001](adr/0001-stack-tecnologico.md): Python 3.11 (64-bit) + Tkinter + PyInstaller |
| Operación sin conexión a internet | Resuelta — 24-08-2026 | [ADR 0002](adr/0002-operacion-offline.md): espejo SQLite local + cola de sincronización idempotente |
| Empaquetado sin contenedores | Resuelta y autorizada — 21-08-2026 | [ADR 0003](adr/0003-empaquetado-sin-contenedores.md): excepción otorgada por la profesora Karla Roco |
| Integración con balanza descartada | Resuelta | Ver sección 4 — se opta por código de barras con peso embebido, no por integración directa con el hardware de la balanza |
| Framework de pruebas | Resuelta | `pytest` + `ruff` (justificado en ADR 0001, sección "Justificación por requerimientos", R6) |

> Las tres filas que esta tabla marcaba antes como "Pendiente" (stack, operación offline,
> framework de pruebas) ya estaban resueltas y documentadas en los ADR desde el
> 24-08-2026 — lo que faltaba era reflejarlo aquí. No son decisiones nuevas de esta
> actualización.

## 1. Stack tecnológico — por qué Python + Tkinter y no otra cosa

El PC del local corre **Windows 8.1 de 64 bits** y no se va a actualizar en el marco de
este proyecto — es la restricción dura que descarta casi todas las alternativas modernas:
Python 3.12+ (rompe soporte a partir de esa versión, PEP 11), Electron 23+ y Tauri
(dejaron de soportar Windows 7/8/8.1), y .NET 7/8 (tampoco corre en 8.1). La opción
elegida, **Python 3.11 (64-bit) + Tkinter + PyInstaller**, es la última versión de
CPython compatible con el equipo real de destino, con Tkinter incluido (sin runtime
externo que instalar) y con `psycopg2-binary` para la conexión a Supabase, que trae su
propio `libpq`/OpenSSL — así el TLS 1.2 hacia Supabase no depende del SChannel de un
Windows sin parches desde 2023. Detalle completo y descartes explícitos:
[ADR 0001](adr/0001-stack-tecnologico.md).

## 2. Operación sin conexión a internet

El sistema legado (Firebird embebido) vende sin depender de internet; escribir siempre
directo a Supabase sería una regresión real frente a lo que el local tiene hoy —
inaceptable para el negocio. Se eligió un **espejo local SQLite + cola de sincronización
idempotente**: la aplicación siempre lee y escribe en SQLite local, y cada operación
(venta, ajuste de stock, alta de producto) se encola con un UUID de cliente para subir a
Supabase cuando hay red, usando `ON CONFLICT (id_cliente) DO NOTHING` para que un
reintento nunca duplique datos. El caso más riesgoso — un corte de energía o de red a
mitad de la sincronización — está cubierto por una prueba automatizada que pasa en la
suite actual:
`tests/integracion/test_cola_sincronizacion.py::test_corte_a_mitad_no_pierde_ni_duplica`.
Detalle completo: [ADR 0002](adr/0002-operacion-offline.md).

## 3. Empaquetado sin contenedores

Se evaluó Docker para portabilidad ("que corra en cualquier PC"), pero se descartó:
Docker Desktop no corre en Windows 8.1 (requiere Windows 10/11 con WSL2/Hyper-V), y la
profesora guía ya eximió al equipo de contenerización porque el sistema no ejecuta nada
como servicio propio — la base de datos en la nube la provee Supabase, un servicio
gestionado por terceros. La portabilidad se cubre por otros mecanismos equivalentes:
ejecutable autocontenido vía PyInstaller, variables de entorno separadas del código,
dependencias fijadas en `requirements.txt`, y esquema de datos versionado en
`database/migraciones/`. El `.exe` debe compilarse en una VM Windows 8.1 (o Windows 7):
hereda la compatibilidad de la máquina donde se construye, y compilar en Windows 10/11
genera un binario que no arranca en el 8.1. Detalle completo:
[ADR 0003](adr/0003-empaquetado-sin-contenedores.md).

## 4. Productos pesables y códigos de barras con peso embebido

Emporio NaturalSur vende por unidad y a granel. Las balanzas de tienda imprimen
etiquetas EAN-13 "internas" (rango GS1 de distribución restringida, prefijos **20-29**)
con el peso o precio del producto pesado embebido en los dígitos centrales del código —
estos códigos no son globales, solo tienen sentido dentro de la tienda. Se decidió
**parsear el código en software** (`src/pos/dominio/codigo_barras.py`) en lugar de
integrar directamente con el hardware de la balanza: el formato de 13 dígitos se
descompone en prefijo interno (posiciones 0-1), código de producto (2-6), valor
embebido — peso en gramos o precio, 5 dígitos (7-11) — y dígito verificador EAN-13
estándar (posición 12). El modo (peso vs. precio) y los decimales del valor quedan
parametrizables porque cada balanza puede configurarse distinto. Esta decisión es la
razón por la que la integración directa con hardware de balanza fue descartada: leer el
código ya impreso es más simple y no depende del modelo específico de balanza del local.

> **Responde al instructivo:** documento de diseño con decisiones técnicas.
