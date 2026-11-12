# Casos de prueba — Emporio NaturalSur

**Versión:** 1.0 · **Fecha:** 11-11-2026 · **Equipo:** Silva, Guzmán, Roa

Este documento describe los casos de prueba del sistema, cómo se ejecutaron y sus resultados. Se
complementa con el *Plan de pruebas y evidencias* (`Fase 2/Evidencias de Proyecto/`) y con el
`registro-de-defectos.md`.

## 1. Estrategia

| Nivel | Qué prueba | Herramienta | Dónde corre |
|---|---|---|---|
| Unitaria | Reglas del dominio (dinero, pagos, lotes, caja, crédito, formato) | `pytest` | Mac (desarrollo), CI Linux, VM Windows 8.1 |
| Integración | Casos de uso con **SQLite real** y, para la sincronización, **PostgreSQL real** (Docker) | `pytest` | ídem |
| Interfaz (E2E) | La aplicación **real** (Tkinter) con sus formularios, en un proceso aparte por escenario | `pytest` + escenarios | ídem |
| Seguridad y rendimiento | Contraseñas, permisos, índices, tiempos de caja | `pytest` | ídem |
| Manual de aceptación (QA) | Recorridos con la app real por Victoria (QA) y por el equipo | Ambiente QA 2 | Mac y Windows 8.1 |

**Criterios de aceptación de un caso:** el resultado obtenido coincide con el esperado y queda
evidencia (resultado de `pytest`, captura o registro en la base). **Criterio de salida:** suite completa
en verde, `ruff` sin errores y los defectos de prioridad Alta cerrados.

## 2. Resumen de resultados (11-11-2026)

La última ejecución completa (Mac, con PostgreSQL en Docker) dio **405 pruebas pasadas, 0 fallidas y 0
omitidas en 22,7 s**.


| Tipo de prueba | Casos automáticos | Resultado |
|---|---|---|
| Integración | 171 | todos pasan |
| Unitaria | 162 | todos pasan |
| Unitaria / regresión | 24 | todos pasan |
| Interfaz (E2E) | 7 | todos pasan |
| Rendimiento | 6 | todos pasan |
| Seguridad | 5 | todos pasan |
| **Total (funciones de prueba)** | **375** | **405 casos pasan / 0 fallan** |


Las 375 funciones se expanden a 405 casos porque varias pruebas están parametrizadas (una función corre con varios datos).

Los 7 archivos de interfaz (E2E) cuentan 1 caso cada uno en `pytest`, pero cada escenario ejecuta muchas
verificaciones con la ventana real: 285 en total (`anular_venta: 19, catalogo: 40, clientes_compras: 43, sesion: 33, ventas: 150`).

**Windows 8.1 (VM, 08-11-2026):** la misma suite pasó allí (337 pasadas, 23 omitidas por no tener
PostgreSQL en la VM, 0 fallidas) y el `.exe` compilado arrancó (ver CP-W-01).

## 3. Casos de aceptación manuales (con la app real)

Cada caso se ejecutó con la aplicación real sobre una **base nueva con datos ficticios**. Los resultados
obtenidos son los valores vistos en pantalla y comprobados en la base de datos.

| ID | Caso | Precondiciones | Pasos y datos | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|---|
| CP-M-01 | Ingreso y perfil de vendedora (HU-USR-01/02) | Base nueva; usuaria `admin` | Ingresar como `admin`; F7 → Usuarios → Nuevo usuario `maria.gonzalez` / `venta2024`, perfil Vendedora; cerrar sesión; ingresar como María; intentar abrir F5 | María solo puede usar F1; F2 a F7 quedan bloqueados | Se creó `maria.gonzalez` (perfil Vendedora); con su cuenta solo F1 está activo y F5 no abre | Aprobado |
| CP-M-02 | Proveedor y factura de compra con lote (HU-CMP-01/02) | Producto Almendras a granel (ALM-GR, costo $7.900, perecible) | F5 → Nuevo proveedor «Frutos del Sur»; Registrar factura N° 45678, neto $42.500, IVA $8.075; línea ALM-GR, 5 kg, $8.500; lote `L2024-001`, vence en 30 días; Confirmar | Factura confirmada; costo $7.900 → $8.500; +5 kg; lote creado | Factura 45678 confirmada; costo neto $8.500; lote `L2024-001` con saldo 5 que vence 2026-12-07 | Aprobado |
| CP-M-03 | Alerta de vencimiento y merma (HU-INV-02/03/04) | Lote de 5 kg que vence en 30 días; aviso a 45 días | F3 → Existencias, Lotes y vencimientos, Alertas; Ajustes y mermas: ALM-GR, 0,1 kg, motivo «Rotura» | Alerta con 10 % de descuento sugerido; la merma baja el stock a 4,9 kg | Alerta: 30 días, precio $14.990, descuento 10 %, precio sugerido $13.491; existencia y lote en 4,9 | Aprobado |
| CP-M-04 | Cliente con crédito (HU-CLI-01) | — | F4 → Nuevo cliente: Juan Pérez, teléfono +56 9 1234 5678 | Cliente creado con saldo $0 | Juan Pérez aparece en la lista, activo, saldo $0 | Aprobado |
| CP-M-05 | Jornada y venta completa (HU-CAJ-01, HU-VTA-01/03/04/09) | Fondo en billetes; Almendras $14.990/kg; Mix $3.990 | Abrir jornada (2×$20.000 + 1×$10.000); venta 1: ALM-GR 0,350 kg, descuento 15 % «Cliente frecuente», pago en efectivo entregando $20.000; venta 2: 2 Mix a crédito de Juan | Venta 1: total $4.460 y vuelto $15.540; venta 2: $7.980 a la cuenta de Juan | Fondo $50.000; descuento $787; efectivo $4.460 (entregó $20.000, vuelto $15.540); crédito $7.980; stock Mix 20 → 18 | Aprobado |
| CP-M-06 | Cuenta, abono y estado de cuenta (HU-CLI-02/03/04) | Consumo a crédito de $7.980 | F4 → Ver cuenta; Registrar abono $5.000 por transferencia; Estado de cuenta del ciclo | Saldo $2.980; el estado descuenta el 20 % | Consumos $7.980; descuento 20 % −$1.596; total a pagar $6.384; abonos $5.000; saldo final $2.980 | Aprobado |
| CP-M-07 | Reportes y auditoría (HU-REP-02/03, HU-USR-03) | Ventas del día | F6 → Ventas (hoy) y Rentabilidad; F7 → Auditoría | Totales de ventas y margen; cada cambio sensible auditado | 2 ventas, total $12.440, ticket promedio $6.220; ganancia $3.079 sobre $10.454 netos (29,5 %); 5 registros de auditoría | Aprobado |
| CP-M-08 | Anular una venta (HU-VTA-11) | Jornada abierta con una venta en efectivo ($3.990) y una a crédito de Juan ($7.980) | F1 → Caja y corte → Anular venta; elegir la venta de $7.980; motivo «Producto en mal estado»; confirmar | Venta marcada anulada; stock vuelve; consumo revertido; el corte la muestra aparte; auditoría | Venta 2 anulada con motivo y autor; stock Mix 17 → 19; cuenta de Juan con consumo y su «Anulación» (saldo $0); corte: «Ventas anuladas (1) $7.980»; auditoría y operación de sincronización registradas | Aprobado |
| CP-M-09 | Cupo de crédito (CL-01) | Juan Pérez con cupo $5.000 | F1: vender $7.980 a crédito a Juan; luego vender $3.990 | $7.980 se rechaza con aviso del cupo restante; $3.990 pasa | Rechazo: «le quedan $5.000 y esta venta a crédito es de $7.980»; $3.990 se registró; el cobro muestra «cupo disponible» | Aprobado |

### 3.1 Regresión manual de los hallazgos del QA del 09-11 (10-11-2026, macOS)

| ID | Hallazgo | Pasos | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| CP-R-01 | O-31 | F10 → buscar «viejo» (producto desactivado) y elegirlo | Lista con «(desactivado)» en gris; el aviso sale antes de agregar | «Producto viejo (desactivado)» en gris y el aviso «El producto … está desactivado» | Aprobado |
| CP-R-02 | O-38 | Abrir F10 con varios productos | Botón siempre visible y lista con barra de desplazamiento | La ventana tiene alto fijo, barra y botón «Seleccionar» visible | Aprobado |
| CP-R-03 | O-35 | Caja y corte → Movimiento de caja → tipo ingreso | Solo «Ingreso de sencillo» | El ingreso ofrece únicamente «Ingreso de sencillo» | Aprobado |
| CP-R-04 | O-37 | Vender un producto con dos lotes y cambiar de lote con F11 | Lote legible y fechas día-mes | «L-A (vence 30-11)»; con F11: «L-B (vence 09-01-2027) · elegido», completo | Aprobado |
| CP-R-05 | O-39 | Resumen del día → clic en «Ver →» del aviso «sin costo» | El aviso nombra el producto y abre F2 filtrado | «Té verde 100 g (sin costo)…»; un clic abre F2 con «Sin costo» y solo ese producto | Aprobado |
| CP-R-06 | CA-18 | F4 → Cuenta → escribir «ju» en Cliente | La lista se despliega y se acorta | Aparece «Juan Pérez» sin quitar el foco al campo | Aprobado |
| CP-R-07 | CL-04 | F4 → Cuenta y Estado de cuenta | Selector de cliente y ciclo actual por defecto | Ambas pestañas tienen selector; ciclo «Noviembre 2026» elegido | Aprobado |
| CP-R-08 | CL-03 | F4 → Estado de cuenta con un consumo | Consumos, descuento en pesos y total a pagar | Consumos $3.990; descuento 20 % −$798; total a pagar $3.192 | Aprobado |
| CP-R-09 | CL-01 | Ver CP-M-09 | Cupo visible y bloqueo al superarlo | Lista: Cupo $5.000 y Disponible $5.000; pestaña Cuenta con cupo y disponible | Aprobado |

### 3.2 Prueba en Windows 8.1 (VM, 08-11-2026)

| ID | Caso | Pasos | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| CP-W-01 | Arranque del `.exe` | Compilar con PyInstaller en la VM; abrir con base temporal sin Supabase | El proceso sigue abierto y crea la base | Siguió abierto a los 10 s; base con 23 tablas y 20 categorías | Aprobado |
| CP-W-02 | Venta en efectivo en la ventana real | Ingresar como `admin`; abrir jornada $50.000; vender 1 Mix pagando con $5.000 | «Venta #1 registrada»; vuelto $1.010 | «Venta #1 registrada con éxito. Cambio a entregar: $1.010»; stock 20 → 19 | Aprobado |
| CP-W-03 | Reportes | F6 → Ventas | 1 venta por $3.990 | «1 venta · total $3.990 · ticket promedio $3.990» | Aprobado |
| CP-W-04 | Suite automática en la VM | `pytest tests` con Python 3.11.9 de 64 bits | Sin fallas | 337 pasadas, 23 omitidas (sin PostgreSQL), 0 fallidas | Aprobado |
| CP-W-05 | Impresora real | Imprimir un comprobante | Sale por la Xprinter | **No se ha probado** (falta el equipo) | Pendiente |

Hallazgo de interfaz en esa pantalla (1024 × 768): la barra de botones de F1 y una tabla de Reportes se cortaban;
las pestañas largas llevan barra de desplazamiento y la ventana se ajusta a la pantalla.

## 4. Casos manuales de QA del 29-10 (`Q-01` a `Q-15`)

Primera ronda de verificación del ambiente de prueba, ejecutada por QA el 29-10-2026. El resultado es el de esa fecha; las fallas están en el registro de defectos y se corrigieron en las rondas siguientes.

| ID | Área | Paso | Resultado esperado | Resultado 29-10 | Observación |
|---|---|---|---|---|---|
| Q-01 | General | Ejecuta 7_preparar_QA.bat y mira el final | Pruebas en verde y «All checks passed!». Anota cuántas pasaron | OK | 199 pruebas pasaron y 11 se omitieron. ruff dice «All checks passed!». Las omitidas necesitan la base Postgres (POS_TEST_PG_URL)… |
| Q-02 | Acceso | Abre 2_abrir_sistema.bat por primera vez | Pide crear la contraseña de administradora; luego pide iniciar sesión | Falla | Al abrir 2_abrir_sistema.bat la ventana queda en negro y no aparece el cuadro para crear la contraseña. Se registra como hallazgo… |
| Q-03 | Acceso | Cierra, vuelve a abrir y escribe una contraseña equivocada | Rechaza sin decir si falló el usuario o la contraseña | No aplica | No se puede probar porque depende de Q-02. |
| Q-04 | General | Recorre F1 a F7 con las teclas | Una sola ventana, franja de color por módulo. F4, F5 y F7 muestran que están pendientes | OK | La navegación F1 a F7 funciona en una sola ventana. |
| Q-05 | Catálogo F2 | Crea un producto sin categoría | Rechaza el alta | OK | Rechaza el alta de un producto sin categoría. |
| Q-06 | Catálogo F2 | Abre la lista de categorías | Muestra las categorías reales desde la base (hoy se espera que muestre 4 fijas: frutas, v… | Parcial | La lista desplegable funciona, pero tiene 4 categorías fijas en el código y la tabla muestra el número. Faltan las 20 categorías… |
| Q-07 | Catálogo F2 | Busca «Te verde» (sin costo) o escribe costo 0 y precio 1000 | Margen y markup dicen «falta costo», no 100 % | Falla | Revisado antes. Con costo 0 muestra margen 100 % en vez de «falta costo». C-06 rechazado. |
| Q-08 | Catálogo F2 | Crea un producto con costo 1190, ciérralo y reábrelo | El costo se mantiene igual al ingresado | OK | Revisado antes. El costo se mantiene al reabrir. C-05b aprobado. |
| Q-09 | Inventario F3 | Ingresa stock a un producto recién creado | Queda con existencia y se puede vender en F1 | OK | Se ingresó stock al café y al soju en F3 («Stock ingresado») y ambos se vendieron en F1. La diferencia: F2 crea la ficha del prod… |
| Q-10 | Inventario F3 | Crea dos lotes del mismo producto con vencimientos distintos | Se listan ordenados por vencimiento | Falla | F3 no tiene lista de lotes, solo alertas. No se puede ver los lotes de un producto ordenados por vencimiento. |
| Q-11 | Inventario F3 | Deja un lote que venza dentro del plazo de aviso | Aparece en alertas con descuento sugerido; no se aplica solo | OK | El soju (vence 2026-10-30, 1 día) aparece en alertas con 30 % de descuento sugerido ($5.003 → $3.502). El precio no cambió solo:… |
| Q-12 | Venta F1 | Vende ese producto con el lector | Propone el lote más próximo a vencer | No aplica | F1 no muestra de qué lote sale el producto, así que no se puede verificar que use el que vence antes. |
| Q-13 | Venta F1 | Repite D-01 a F-04 del registro (venta, pagos mixtos, vuelto, quitar línea) | Siguen corregidos en la ventana única | Parcial | F1 no muestra de qué lote sale el producto, así que no se puede verificar que use el que vence antes. + Nuevo D-27: el cobro en e… |
| Q-14 | Reportes F6 | Consulta ventas de hoy por categoría | Monto y porcentaje por categoría; ninguna venta sin categoría | OK | Reporte del 29-10: 4 ventas, total $87.270, ticket promedio $21.818. Mejora H-01: calendario para elegir la fecha |
| Q-15 | Caja F1 | Cierra la jornada con conteo por denominación | Muestra el arqueo con diferencia |  |  |

## 5. Casos automáticos (por archivo)

Total: **375** funciones de prueba en 52 archivos. «HU» son las historias de usuario que cita el archivo (trazabilidad).

| N° | Archivo | Tipo | Casos | Qué verifica | Historias de usuario |
|---|---|---|---|---|---|
| CP-A-01 | `tests/e2e/test_anular_venta_gui.py` | Interfaz (E2E) | 1 | HU-VTA-11: anular una venta desde la pantalla de Caja y corte (app real, proceso aparte). | HU-VTA-11 |
| CP-A-02 | `tests/e2e/test_catalogo_gui.py` | Interfaz (E2E) | 1 | F2 Catalogo con la app real: ficha, historial y categorias (proceso aparte). | — |
| CP-A-03 | `tests/e2e/test_clientes_compras_gui.py` | Interfaz (E2E) | 1 | F4 Clientes y F5 Compras con la app real y sus formularios (proceso aparte). | — |
| CP-A-04 | `tests/e2e/test_flujo_completo_gui.py` | Interfaz (E2E) | 1 | Prueba de punta a punta con la APLICACION REAL (Tk) y PostgreSQL real. | — |
| CP-A-05 | `tests/e2e/test_login_visible.py` | Interfaz (E2E) | 1 | A-03: el cuadro de acceso debe verse. Se corre en un proceso aparte (una sola ventana Tk). | — |
| CP-A-06 | `tests/e2e/test_sesion_gui.py` | Interfaz (E2E) | 1 | F7 con la app real: usuarios, perfiles, cierre de sesion e inactividad (proceso aparte). | — |
| CP-A-07 | `tests/e2e/test_ventas_gui.py` | Interfaz (E2E) | 1 | O-25, O-30 y O-02b con la pantalla F1 real. Corre en un proceso aparte (una ventana Tk). | — |
| CP-A-08 | `tests/integracion/test_administracion.py` | Integración | 9 | F7 Administracion: usuarios y perfiles, auditoria, configuracion y permisos (SQLite real). | — |
| CP-A-09 | `tests/integracion/test_anular_venta.py` | Integración | 12 | HU-VTA-11: anular una venta cobrada, con motivo, sin borrarla (SQLite real, datos ficticios). | HU-VTA-11 |
| CP-A-10 | `tests/integracion/test_catalogo.py` | Integración | 12 | F2 Catalogo: lista con filtros, categorias (CA-16) e historial de precios (SQLite real). | — |
| CP-A-11 | `tests/integracion/test_categorias.py` | Integración | 7 | Categorias en tabla (C-02): semilla, carga de la lista de la PO y sincronizacion. | — |
| CP-A-12 | `tests/integracion/test_clientes.py` | Integración | 18 | Credito a clientes (HU-CLI-01 a 05, HU-CAJ-03) con SQLite real. Datos ficticios. | HU-CAJ-03, HU-CLI-01, HU-CLI-04 |
| CP-A-13 | `tests/integracion/test_cola_sincronizacion.py` | Integración | 3 | Pruebas de la cola de sincronizacion offline y del caso de uso de sincronizacion. | — |
| CP-A-14 | `tests/integracion/test_compras.py` | Integración | 7 | Factura de compra (HU-CMP-01/02): el detalle actualiza el costo y crea el lote (SQLite real). | HU-CMP-01 |
| CP-A-15 | `tests/integracion/test_impresion.py` | Integración | 12 | HU-VTA-06: comprobante, reimpresion, corte y cajon (SQLite real, impresora simulada). | HU-VTA-06 |
| CP-A-16 | `tests/integracion/test_inventario_consultas.py` | Integración | 9 | HU-INV-05 stock minimo, HU-INV-07 inventario valorizado y HU-INV-08 movimientos. | HU-INV-05, HU-INV-07, HU-INV-08 |
| CP-A-17 | `tests/integracion/test_inventario_lotes.py` | Integración | 13 | Ingreso de stock con lote, alertas de vencimiento y consumo FEFO (SQLite real). | HU-INV-04 |
| CP-A-18 | `tests/integracion/test_permisos_pos_app.py` | Integración | 3 | El rol pos_app puede operar TODAS las tablas del schema pos (PostgreSQL real). | — |
| CP-A-19 | `tests/integracion/test_proveedores.py` | Integración | 11 | Proveedores (HU-CMP-03): crear, no duplicar y mezclar los creados con los de las facturas. | HU-CMP-03 |
| CP-A-20 | `tests/integracion/test_rentabilidad_rotacion.py` | Integración | 8 | HU-REP-03 rentabilidad, HU-REP-04 rotacion y HU-PRD-06 desactivar (SQLite real). | HU-PRD-06, HU-REP-03, HU-REP-04 |
| CP-A-21 | `tests/integracion/test_reporte_ventas.py` | Integración | 4 | Reporte de ventas por periodo y categoria con SQLite real (HU-REP-02). | HU-REP-02 |
| CP-A-22 | `tests/integracion/test_repositorio_sqlite.py` | Integración | 5 | Pruebas de integracion de los repositorios contra SQLite real (base en memoria). | — |
| CP-A-23 | `tests/integracion/test_resumen_del_dia.py` | Integración | 5 | HU-REP-01 / HU-REP-05: resumen del dia con venta, ganancia, meta y avisos (SQLite real). | HU-REP-01, HU-REP-05 |
| CP-A-24 | `tests/integracion/test_sync_clientes_compras.py` | Integración | 8 | Clientes, credito, proveedores, facturas y auditoria encolan su operacion (migracion 008). | — |
| CP-A-25 | `tests/integracion/test_sync_postgres.py` | Integración | 7 | Sincronizacion SQLite -> PostgreSQL REAL (schema `pos`), de punta a punta. | — |
| CP-A-26 | `tests/integracion/test_sync_postgres_pantallas.py` | Integración | 6 | Lo que agregaron las pantallas nuevas llega a PostgreSQL REAL (schema `pos`, migracion 007). | HU-VTA-11 |
| CP-A-27 | `tests/integracion/test_ventas_caja_e2e.py` | Integración | 12 | Pruebas end-to-end del flujo de venta y caja contra SQLite real (base en memoria). | HU-CAJ-01, HU-CAJ-02, HU-CAJ-03, HU-CAJ-04, HU-VTA-01, HU-VTA-03, HU-VTA-04 |
| CP-A-28 | `tests/rendimiento/test_indices_lectura.py` | Rendimiento | 4 | Las lecturas calientes usan indice: sin ellos los reportes son cuadraticos con el historial. | — |
| CP-A-29 | `tests/rendimiento/test_rendimiento_caja.py` | Rendimiento | 2 | Rendimiento en caja: con un catalogo grande, buscar y vender deben seguir siendo agiles. | — |
| CP-A-30 | `tests/seguridad/test_seguridad_basica.py` | Seguridad | 5 | Seguridad basica: credenciales fuera del repo, inyeccion SQL y claves hasheadas. | — |
| CP-A-31 | `tests/test_dominio_productos.py` | Unitaria / regresión | 8 | Pruebas de regresion QA para el dominio de productos. | — |
| CP-A-32 | `tests/test_interfaz_productos_regresion.py` | Unitaria / regresión | 11 | Pruebas de regresion QA para la interfaz Tkinter de productos. | — |
| CP-A-33 | `tests/test_repositorio_sqlite.py` | Unitaria / regresión | 5 | Pruebas de regresion QA para el repositorio SQLite de productos. | — |
| CP-A-34 | `tests/unitarias/test_caja.py` | Unitaria | 12 | Pruebas de turno de caja, movimientos y arqueo de cierre. | HU-CAJ-01, HU-CAJ-02, HU-CAJ-04 |
| CP-A-35 | `tests/unitarias/test_casos_uso.py` | Unitaria | 9 | Pruebas de los casos de uso con dobles en memoria (sin infraestructura real). | HU-INV-04 |
| CP-A-36 | `tests/unitarias/test_codigo_barras.py` | Unitaria | 15 | Pruebas del parser de codigos de barras EAN-13 con peso/precio embebido. | — |
| CP-A-37 | `tests/unitarias/test_combo_filtrable.py` | Unitaria | 8 | CA-18: los desplegables de categoria filtran lo escrito sin distinguir tildes ni mayusculas. | — |
| CP-A-38 | `tests/unitarias/test_costo.py` | Unitaria | 3 | Pruebas del value object Costo (HU-PRD-02: neto, IVA e impuesto adicional separados). | HU-PRD-02 |
| CP-A-39 | `tests/unitarias/test_costos_impuestos.py` | Unitaria | 4 | Pruebas de costos, impuestos y rentabilidad (HU-PRD-02 y HU-PRD-03). | HU-PRD-02, HU-PRD-03 |
| CP-A-40 | `tests/unitarias/test_desplazable.py` | Unitaria | 1 | MarcoDesplazable: lo que no cabe en la ventana se alcanza con scroll (Caja y corte). | — |
| CP-A-41 | `tests/unitarias/test_dinero.py` | Unitaria | 4 | Pruebas de la politica de redondeo del value object Dinero (HALF_UP explicito). | — |
| CP-A-42 | `tests/unitarias/test_formato.py` | Unitaria | 6 | Formato y lectura de montos CLP (O-07): una sola funcion para toda la app. | — |
| CP-A-43 | `tests/unitarias/test_inventario.py` | Unitaria | 5 | Pruebas de las reglas de inventario (Existencia). | — |
| CP-A-44 | `tests/unitarias/test_login.py` | Unitaria | 6 | Login con bcrypt (HU-USR-01): hash, autenticacion y no revelar que dato fallo. | HU-USR-01 |
| CP-A-45 | `tests/unitarias/test_lotes.py` | Unitaria | 10 | Lotes, FEFO y politica de descuento sugerido (HU-INV-02, HU-INV-03, HU-INV-06). | HU-INV-02, HU-INV-03, HU-INV-06 |
| CP-A-46 | `tests/unitarias/test_migraciones.py` | Unitaria | 2 | Guardas sobre los archivos de migracion (no requieren base de datos). | — |
| CP-A-47 | `tests/unitarias/test_pagos.py` | Unitaria | 12 | Pruebas de medios de pago, redondeo en efectivo y conteo por denominacion. | HU-VTA-03, HU-VTA-04 |
| CP-A-48 | `tests/unitarias/test_productos.py` | Unitaria | 13 | Pruebas de la entidad Producto y del value object Dinero. | HU-PRD-03, HU-PRD-08 |
| CP-A-49 | `tests/unitarias/test_traductor_supabase.py` | Unitaria | 22 | Pruebas del traductor de operaciones de sincronizacion a SQL de PostgreSQL. | HU-VTA-11 |
| CP-A-50 | `tests/unitarias/test_ventana_principal.py` | Unitaria | 6 | Ventana unica F1-F7 (GEN-01). Las pruebas con Tk se omiten si no hay entorno grafico. | — |
| CP-A-51 | `tests/unitarias/test_ventas.py` | Unitaria | 20 | Pruebas de la entidad Venta: lineas, totales y cierre con pagos combinados. | HU-VTA-01, HU-VTA-03, HU-VTA-04 |
| CP-A-52 | `tests/unitarias/test_verificar_supabase.py` | Unitaria | 4 | El comparador de esquema (scripts/verificar_supabase.py) entiende las migraciones reales. | — |

## 6. Trazabilidad: historia de usuario → pruebas

| Historia | Archivos de prueba que la cubren |
|---|---|
| HU-CAJ-01 | `test_caja.py`, `test_ventas_caja_e2e.py` |
| HU-CAJ-02 | `test_caja.py`, `test_ventas_caja_e2e.py` |
| HU-CAJ-03 | `test_clientes.py`, `test_ventas_caja_e2e.py` |
| HU-CAJ-04 | `test_caja.py`, `test_ventas_caja_e2e.py` |
| HU-CLI-01 | `test_clientes.py` |
| HU-CLI-04 | `test_clientes.py` |
| HU-CMP-01 | `test_compras.py` |
| HU-CMP-03 | `test_proveedores.py` |
| HU-INV-02 | `test_lotes.py` |
| HU-INV-03 | `test_lotes.py` |
| HU-INV-04 | `test_casos_uso.py`, `test_inventario_lotes.py` |
| HU-INV-05 | `test_inventario_consultas.py` |
| HU-INV-06 | `test_lotes.py` |
| HU-INV-07 | `test_inventario_consultas.py` |
| HU-INV-08 | `test_inventario_consultas.py` |
| HU-PRD-02 | `test_costo.py`, `test_costos_impuestos.py` |
| HU-PRD-03 | `test_costos_impuestos.py`, `test_productos.py` |
| HU-PRD-06 | `test_rentabilidad_rotacion.py` |
| HU-PRD-08 | `test_productos.py` |
| HU-REP-01 | `test_resumen_del_dia.py` |
| HU-REP-02 | `test_reporte_ventas.py` |
| HU-REP-03 | `test_rentabilidad_rotacion.py` |
| HU-REP-04 | `test_rentabilidad_rotacion.py` |
| HU-REP-05 | `test_resumen_del_dia.py` |
| HU-USR-01 | `test_login.py` |
| HU-VTA-01 | `test_ventas.py`, `test_ventas_caja_e2e.py` |
| HU-VTA-03 | `test_pagos.py`, `test_ventas.py`, `test_ventas_caja_e2e.py` |
| HU-VTA-04 | `test_pagos.py`, `test_ventas.py`, `test_ventas_caja_e2e.py` |
| HU-VTA-06 | `test_impresion.py` |
| HU-VTA-11 | `test_anular_venta.py`, `test_anular_venta_gui.py`, `test_sync_postgres_pantallas.py`, `test_traductor_supabase.py` |

Historias citadas por alguna prueba: **30** de 49 del backlog v4.3. Las que no aparecen aquí se verifican de forma manual (secciones 3 y 4) o están fuera del alcance entregado (por ejemplo, la migración de datos del sistema antiguo).

## 7. Ejecutar las pruebas

```bash
ruff check . && ruff format --check .
POS_TEST_PG_URL=postgresql://postgres:postgres@localhost:55432/postgres python -m pytest tests -q -p no:warnings
```

Los escenarios de interfaz corren cada uno en su propio proceso (Tk admite una sola ventana raíz por proceso): por ejemplo
`python -I tests/e2e/escenario_anular_venta_gui.py`.
