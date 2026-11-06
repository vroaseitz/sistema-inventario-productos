# 04 · Requisitos no funcionales

Restricciones del sistema, más allá de lo que hace. Cada punto distingue lo que ya está
**resuelto y verificable en el código** de lo que es **propuesta de Fernando, a confirmar
con el equipo** — para no documentar como decisión de equipo algo que todavía no se
conversó con Victoria y Eduardo.

## 1. Seguridad

**Resuelto (esquema de datos):**

- El modelo de datos (`database/migraciones/002_modelo_completo.sql`,
  `docs/06-modelo-datos/`) nunca guarda la contraseña en texto plano: la tabla `usuario`
  tiene `contrasena_hash`, no `contrasena`.
- Toda operación relevante queda auditada: la tabla `auditoria` registra
  `usuario_id`, `tabla`, `accion`, `datos_antes` y `datos_despues` (JSONB) — corrige el
  hallazgo del análisis del sistema legado, donde la tabla equivalente estaba vacía
  (`docs/06-modelo-datos/README.md`, corrección #7).
- Perfil único con auditoría, sin roles diferenciados todavía: fue una decisión de
  alcance explícita del equipo (16-09-2026, documentada en `docs/06-modelo-datos/README.md`
  corrección #8) — se prioriza login + auditoría; el control de acceso por roles queda
  como incremento posterior, sin tarea ni fecha asignada aún.

**Propuesta de Fernando — a confirmar con el equipo:**

- El algoritmo concreto de hash de contraseña (ej. `bcrypt` vía `passlib`, o
  `hashlib.scrypt` de la librería estándar) todavía no está implementado en
  `src/pos` ni decidido por el equipo. Propongo `bcrypt`/`passlib` por ser el estándar
  de facto y no requerir compilar nada adicional en la VM Windows 8.1 de destino.
- Las credenciales de Supabase (`.env`, nunca versionado — ver `.gitignore`) deben
  rotarse si alguna vez se compartieron por un canal no cifrado (ej. WhatsApp) durante
  el desarrollo.

## 2. Rendimiento

**Resuelto (por diseño de arquitectura, ADR 0002):**

- La operación de caja (registrar venta, ajustar stock, buscar producto) **siempre lee y
  escribe contra el espejo SQLite local**, nunca contra Supabase en el momento de la
  operación (`docs/08-diseno/adr/0002-operacion-offline.md`). Esto significa que el
  tiempo de respuesta percibido por quien cobra no depende de la latencia de red ni del
  estado de la conexión a internet.

**Propuesta de Fernando — a confirmar con el equipo:**

- No hay todavía un número de referencia acordado con el equipo para "tiempo de
  respuesta aceptable". Propongo como objetivo de trabajo (no medido aún con carga real):
  registrar una venta de una línea en menos de 300 ms percibidos en el PC del local, y
  que la sincronización en segundo plano hacia Supabase nunca bloquee la pantalla de venta.
  Esto habría que validarlo con una prueba de carga sobre la VM Windows 8.1 antes de
  cerrarlo como requisito firme.

## 3. Disponibilidad

**Resuelto, implementado y probado:**

- Ante una caída de la conexión a internet, el sistema sigue vendiendo: arquitectura de
  **espejo local SQLite + cola de sincronización idempotente** hacia Supabase
  (`docs/08-diseno/adr/0002-operacion-offline.md`).
- El caso crítico — un corte de energía o de red **a mitad** de la sincronización — no
  pierde ni duplica datos, gracias a la idempotencia por `id_cliente` (UUID) y a
  `ON CONFLICT (id_cliente) DO NOTHING` en el destino. Esto no es una afirmación de
  diseño sin verificar: está cubierto por la prueba automatizada
  `tests/integracion/test_cola_sincronizacion.py::test_corte_a_mitad_no_pierde_ni_duplica`,
  que pasa en la suite actual (69/69 pruebas, ver `docs/11-pruebas/`).
- SQLite corre en modo WAL con `synchronous=NORMAL`: las transacciones locales son
  atómicas y recuperables ante un corte de energía del PC del local.

## 4. Escalabilidad

**Resuelto (es consecuencia directa del cambio de motor de base de datos):**

- El sistema legado usa **Firebird embebido**, que admite una sola conexión activa: no
  es posible acceder desde otro equipo ni agregar una segunda caja sin reemplazar el
  motor (hallazgo documentado en `README.md`, tabla de comparación del sistema antiguo).
- El sistema nuevo usa **Supabase/PostgreSQL** como backend remoto, que sí admite
  múltiples conexiones concurrentes. Agregar una segunda caja no requiere cambios de
  arquitectura: cada caja corre su propio espejo SQLite local y su propia cola de
  sincronización, y ambas convergen al mismo Supabase.

**Propuesta de Fernando — a confirmar con el equipo:**

- No se ha probado todavía con dos instancias reales escribiendo a la vez (dos cajas
  simultáneas). Antes de ofrecerlo como capacidad demostrable en una entrega, habría que
  ensayarlo una vez con dos espejos SQLite distintos sincronizando al mismo Supabase.

## 5. Portabilidad

**Resuelto y autorizado:**

- Reemplaza el punto de contenedores del instructivo: la excepción de contenerización
  fue **autorizada por la profesora guía el 21-08-2026**
  (`docs/08-diseno/adr/0003-empaquetado-sin-contenedores.md`). Docker Desktop no corre en
  Windows 8.1 (requiere Windows 10/11 con WSL2/Hyper-V), así que no era viable para el
  equipo de destino real de todos modos.
- La aplicación se distribuye como **ejecutable autocontenido empaquetado con
  PyInstaller** (`build/pos.spec`), ya construido y probado arrancando en la VM Windows
  8.1 de referencia.
- Instalación/traslado a otro equipo: copiar el ejecutable generado y el archivo
  `.env` con las credenciales de Supabase de ese local (nunca versionado). No requiere
  instalar Python ni ninguna dependencia en el equipo destino.
- Restricción dura que condiciona todo lo demás: el build debe compilarse **en una VM
  Windows 8.1** (o Windows 7), nunca en Windows 10/11 — el `.exe` hereda la compatibilidad
  de la máquina donde se construye (`docs/08-diseno/adr/0001-stack-tecnologico.md`).

> **Responde al instructivo:** requisitos no funcionales (obligatorio transversal).
>
> La portabilidad es especialmente relevante: reemplaza el punto de contenedores, cuya
> excepción fue autorizada por la profesora guía.
