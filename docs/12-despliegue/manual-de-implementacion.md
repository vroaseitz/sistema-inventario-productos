# Manual de implementación — Emporio NaturalSur (POS e Inventario)

**Versión:** 1.0 · **Fecha:** 11-11-2026 · **Autores:** equipo Capstone (Silva, Guzmán, Roa)
**Rama de referencia:** `feat/diseno-prototipo` (PR #18 → `integracion`, PR #19 → `main`)

Este manual explica cómo instalar, configurar, poner en marcha, verificar y revertir el sistema. Cubre
dos situaciones: **(A)** preparar el entorno de desarrollo y pruebas y **(B)** construir el `.exe` e
instalarlo en el equipo del local. Lo que todavía no se probó en terreno está marcado con ⚠️.

---

## 1. Qué se despliega

La solución **no usa contenedores ni servidores propios** (excepción autorizada por la profesora guía
el 21-08-2026, ver `docs/08-diseno/adr/0003-empaquetado-sin-contenedores.md`). Son dos piezas:

```text
 PC del local (Windows 8.1, 64 bits)                      Nube (tercero)
┌──────────────────────────────────────┐   cola de       ┌────────────────────────────┐
│ pos-naturalsur.exe (Tkinter)         │   sincronización│ Supabase (PostgreSQL)      │
│  ├─ F1 Operación  F2 Catálogo        │ ───────────────►│ proyecto «Emporio»         │
│  ├─ F3 Inventario F4 Clientes        │  (session pooler│ schema `pos`, rol `pos_app`│
│  ├─ F5 Compras    F6 Reportes        │   IPv4, TLS 1.2)└────────────────────────────┘
│  └─ F7 Administración                │
│ SQLite local (pos_local.db)  ← opera │   Periféricos: impresora térmica USB de 58 mm (Xprinter)
│ sin internet (offline primero)       │   y lector de código de barras con sufijo Enter.
└──────────────────────────────────────┘   La boleta tributaria la emite el terminal TUU (aparte).
```

- La app **vende aunque no haya internet**: todo se guarda en SQLite y lo pendiente queda en una cola
  que se envía a Supabase cuando hay conexión (`Pendientes: N` en la barra inferior).
- Si no hay `SUPABASE_DB_URL`, la app funciona igual en modo local y la barra dice «sin Supabase
  configurado».
- La **Product Owner** y las cajeras solo usan la aplicación; nunca tocan la base de datos.

## 2. Requisitos

### 2.1 Equipo del local (donde corre el sistema)

| Requisito | Detalle |
| --- | --- |
| Sistema operativo | **Windows 8.1, 64 bits** (el binario se compila en esa versión; ver 6.1) |
| Pantalla | Se probó a **1024 × 768**; la ventana se ajusta a la pantalla y las pestañas largas tienen barra de desplazamiento |
| Red | Opcional para vender; necesaria para sincronizar (HTTPS/TLS 1.2 hacia Supabase, puerto 5432) |
| Impresora | Xprinter térmica de 58 mm por USB. ⚠️ La impresión real no se ha probado todavía (ver 9) |
| Lector de códigos | Debe enviar **Enter** al final de cada lectura (se configura con el código del manual del lector) |
| Python | **No se necesita**: el `.exe` lleva su propio intérprete |

### 2.2 Equipo de desarrollo / compilación

| Componente | Versión | Para qué |
| --- | --- | --- |
| Python | **3.11 (64 bits)** para compilar; 3.12 también corre el código | Intérprete |
| Tkinter | incluido con Python | Interfaz |
| Dependencias | `requirements.txt`: `python-dotenv`, `psycopg2-binary`, `bcrypt`, `pywin32` (solo Windows) | Ejecución |
| Herramientas | `requirements-dev.txt`: `pytest`, `ruff` | Pruebas y estilo |
| PyInstaller | 6.x | Construir el `.exe` |
| Git | cualquiera reciente | Código |
| Docker | cualquiera reciente | **Solo** para las pruebas contra PostgreSQL (contenedor `pos-pg-test`) |

## 3. Obtener el código y preparar el entorno de desarrollo

```bash
git clone https://github.com/vroaseitz/sistema-inventario-productos.git
cd sistema-inventario-productos
git checkout feat/diseno-prototipo          # o main cuando se integre

python3 -m venv .venv
source .venv/bin/activate                   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

Ejecutar la aplicación en modo desarrollo (con base local y sin nube):

```bash
PYTHONPATH=src POS_SQLITE_PATH=./pos_local.db SUPABASE_DB_URL= python -m pos
```

En Windows (PowerShell): `$env:PYTHONPATH="src"; $env:POS_SQLITE_PATH="pos_local.db"; python -m pos`.

## 4. Configuración

La configuración sale de variables de entorno o de un archivo **`.env` junto al ejecutable**. La
plantilla es `config/.env.example`.

| Variable | Obligatoria | Qué es |
| --- | --- | --- |
| `SUPABASE_DB_URL` | No | URI del **Session Pooler** de Supabase (IPv4, puerto 5432). La conexión directa es solo IPv6 y el equipo del local no la puede usar. Si la contraseña tiene caracteres especiales, se codifican (`@` → `%40`, `#` → `%23`) |
| `POS_SQLITE_PATH` | No | Ruta de la base local. Por defecto `pos_local.db` junto al ejecutable |

> ⚠️ **El `.env` nunca se sube al repositorio** (está en `.gitignore`). Las llaves SSH de la VM y las
> contraseñas se entregan por un canal privado, no por el repo ni por el grupo.

**Parámetros de operación** (se cambian dentro de la app, F7 → Configuración, y quedan en la
auditoría): aviso de vencimiento (14 días por defecto), meta diaria de venta (lunes a viernes
$220.000, sábado $182.000, domingo $88.000), nombre de la impresora, entre otros.

## 5. Bases de datos

### 5.1 Local (SQLite)

- Se **crea y actualiza sola** al abrir la app: `crear_esquema` crea las tablas que faltan y agrega
  las columnas nuevas. No hay que ejecutar nada a mano.
- **Respaldo:** copiar el archivo `.db` con la app cerrada. Es todo lo que hay que guardar.

### 5.2 Remota (Supabase / PostgreSQL)

Las migraciones están en `database/migraciones/` y se aplican **en orden** sobre el schema `pos`:

| N° | Archivo | Qué hace |
| --- | --- | --- |
| 002 | `002_modelo_completo.sql` | Modelo completo (la 001 es un borrador que reemplaza) |
| 003 | `003_retirar_check_precio_bajo_costo.sql` | Permite vender bajo el costo |
| 004 | `004_sincronizacion.sql` | Claves de idempotencia (`id_cliente`) |
| 005 | `005_permisos_pos_app.sql` | Permisos del rol de la aplicación |
| 006 | `006_lotes_sincronizacion.sql` | Lotes en la nube |
| 007 | `007_sincronizacion_pantallas.sql` | Stock mínimo, categorías activas, nota y motivo de descuento, código de lote |
| 008 | `008_sincronizacion_clientes_compras.sql` | Clientes, crédito, proveedores, facturas y auditoría |
| 009 | `009_cupo_credito.sql` | Cupo de crédito por cliente (CL-01) |

**Cómo aplicarlas** (todas son idempotentes: se pueden repetir sin dañar nada):

1. Abrir Supabase → proyecto **Emporio** → *SQL Editor*, con el rol **`postgres`** (dueño de las tablas).
2. Pegar el contenido del archivo y ejecutar. Para la 007 y la 009 hay una copia lista para pegar:
   `007_pegar_en_sql_editor.sql.txt` y `009_pegar_en_sql_editor.sql.txt`.
3. La aplicación se conecta con el rol **`pos_app`**, que **no es dueño** de las tablas: por eso
   ninguna migración se puede aplicar desde la app.

**Verificar el esquema remoto** (solo lectura, no modifica nada):

```bash
python scripts/verificar_supabase.py
```

Compara las tablas y columnas del destino con lo que esperan las migraciones y avisa lo que falta.

## 6. Construir el `.exe` (Windows 8.1)

### 6.1 Por qué se compila en Windows 8.1

El binario hereda la compatibilidad de la máquina donde se construye. Compilar en Windows 10/11 enlaza
DLL (UCRT / `api-ms-win-*`) que **no existen en 8.1** y el programa no arranca allí (ver
`docs/08-diseno/adr/0001-stack-tecnologico.md`). Por eso se usa una **VM con Windows 8.1**. Además,
`psycopg2-binary` trae su propio OpenSSL, de modo que TLS 1.2 hacia Supabase no depende del SChannel
del sistema (clave en 8.1).

### 6.2 Pasos (dentro de la VM con Python 3.11 de 64 bits)

```bat
cd C:\pos-build
"C:\Program Files\Python311\python.exe" -m pip install -r requirements.txt pywin32 pyinstaller
"C:\Program Files\Python311\python.exe" -m PyInstaller build\pos.spec --noconfirm
```

Resultado: carpeta `dist\pos-naturalsur\` con `pos-naturalsur.exe` (~2,4 MB) y la carpeta
`_internal\` con el intérprete y las bibliotecas. **Hay que copiar la carpeta completa**, no solo el `.exe`.

Archivos necesarios en `C:\pos-build`: `src\`, `build\pos.spec`, `requirements.txt` y `pyproject.toml`.
El punto de entrada es `src/pos/__main__.py` (la ventana única F1 a F7).

### 6.3 Acceso a la VM

La VM corre en un servidor AWS (QEMU) y **no está expuesta a internet**: se llega por **túnel SSH con
llave** y se ve la pantalla por VNC o se ejecutan comandos por SSH. Los datos de acceso y las llaves se
entregan por canal privado (`guia-conexion-vm-emporio.md`, sin credenciales). Nunca se escriben en este
repositorio, que es público.

## 7. Instalar en el equipo del local

1. Copiar la carpeta `pos-naturalsur\` al equipo (por ejemplo `C:\NaturalSur\`).
2. Colocar el archivo `.env` (con `SUPABASE_DB_URL`) **junto a `pos-naturalsur.exe`**. Sin él, la app
   funciona en modo local y deja lo pendiente en la cola.
3. Abrir `pos-naturalsur.exe`. En el **primer arranque** pide crear el usuario administrador (con una
   clave de al menos 8 caracteres); luego, en F7 → Usuarios, se crea la cuenta de la vendedora.
4. En F7 → Configuración, elegir la impresora y revisar los parámetros de operación.
5. Abrir la jornada (F1 → Caja y corte → Abrir jornada) contando el fondo en billetes.

## 8. Verificación posterior al despliegue

| # | Comprobación | Resultado esperado |
| --- | --- | --- |
| 1 | Abrir `pos-naturalsur.exe` | Aparece el ingreso; el proceso sigue abierto |
| 2 | Ingresar como administradora | Se ven F1 a F7; la vendedora ve solo F1 |
| 3 | Abrir jornada con $50.000 en billetes | «Turno #1 abierto – fondo inicial $50.000» |
| 4 | Vender un producto en efectivo | «Venta #N registrada», el vuelto coincide, la existencia baja |
| 5 | Vender a crédito a un cliente con cupo | Se carga a su cuenta; sobre el cupo se rechaza con aviso |
| 6 | Anular la venta (F1 → Caja y corte → Anular venta) | Queda marcada, el stock vuelve, el corte la muestra aparte |
| 7 | Sincronizar | «Todo sincronizado»; con `verificar_supabase.py` no faltan columnas |
| 8 | ⚠️ Imprimir comprobante | Sale por la Xprinter (pendiente de probar en terreno) |

**Estado de estas pruebas en Windows 8.1 (11-11-2026):** el `.exe` se compiló y arrancó en la VM, se
abrió en el escritorio, se ingresó como administradora, se abrió la jornada y se vendió y cobró en
efectivo. La suite automática (337 pruebas) pasó en esa misma VM. Quedan sin probar allí el cupo, las
anulaciones y el estado de cuenta, la impresora real y la sincronización contra el Supabase real.

## 9. Actualizar a una versión nueva

1. Cerrar la app y **copiar el `.db`** (respaldo).
2. Aplicar en Supabase las migraciones nuevas, **antes** de abrir la versión nueva.
3. Reemplazar la carpeta `pos-naturalsur\` conservando el `.env` y el `.db`.
4. Abrir la app: el esquema local se actualiza solo.

## 10. Reversa

- **Datos:** volver a copiar el `.db` respaldado y abrir la versión anterior.
- **Programa:** conservar la carpeta de la versión anterior; para volver, abrir su `.exe`.
- **Migraciones de Supabase:** son aditivas (agregan columnas, no borran); no requieren reversa para
  que la versión anterior siga funcionando.
- **Plan de contingencia del local:** el sistema antiguo se conserva intacto durante los primeros días
  (ver `README.md`, plan de reversa).

## 11. Problemas conocidos y qué hacer

| Síntoma | Causa y solución |
| --- | --- |
| La barra dice «Pendientes: N (sin Supabase configurado)» | No hay `SUPABASE_DB_URL` en el `.env`. Es normal en modo local |
| La sincronización se corta en una operación | La cola se detiene en el primer fallo y reintenta después, sin perder nada. Revisar que la migración 009 esté aplicada |
| Al escribir el usuario sale en mayúsculas | Bloq Mayús activado en el equipo |
| Una columna de la tabla se corta en pantallas chicas | Las pestañas largas tienen barra de desplazamiento; la ventana se ajusta a 1024 × 768 |
| En macOS (solo desarrollo) un cuadro se ve negro | Tk 9 lo dibuja al primer clic; no se ha visto en Windows |
| No imprime | Revisar el nombre de la impresora en F7 → Configuración y que `pywin32` esté en el empaquetado ⚠️ |

## 12. Seguridad

- Contraseñas de usuarios guardadas con **bcrypt**; nunca en texto plano.
- Perfiles: **Administradora** (todo) y **Vendedora** (solo F1). Solo la administradora anula ventas.
- El `.env`, las llaves SSH y las contraseñas de la VM y de Supabase **no se versionan**.
- La aplicación usa el rol `pos_app` (sin permisos de dueño) para hablar con Supabase.
- Cada cambio sensible (descuentos, mermas, anulaciones, precios, usuarios) queda en la **auditoría**
  con usuario, fecha, antes y después.

## 13. Pruebas y calidad (para quien instale desde el código)

```bash
ruff check . && ruff format --check .
POS_TEST_PG_URL=postgresql://postgres:postgres@localhost:55432/postgres python -m pytest tests -q -p no:warnings
```

Sin `POS_TEST_PG_URL` se omiten las pruebas contra PostgreSQL. El detalle de los casos está en
`docs/11-pruebas/casos-de-prueba.md` y los defectos encontrados en `docs/11-pruebas/registro-de-defectos.md`.
