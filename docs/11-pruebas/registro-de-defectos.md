# Registro de defectos por ciclos de prueba — Emporio NaturalSur

**Versión:** 1.1 · **Fecha:** 11-11-2026 · **Responsable QA:** Victoria Roa · **Desarrollo:** Silva, Guzmán

Este registro reúne **todos los defectos y hallazgos** que el QA (Victoria Roa) reportó en las seis rondas
de prueba, con su prioridad, quién los corrige, el estado actual y cómo se corrigieron. La fuente es el
Excel `Hallazgos-QA_NaturalSur.xlsx` (una hoja por módulo, evidencias en la carpeta *Capston › QA ›
Evidencia - Fotos*, nombradas con el ID del caso) y el informe «QA 09-11 — hallazgos para corregir».
Los casos de prueba están en `casos-de-prueba.md`.

## 1. Cómo se clasifican

| Prioridad | Significado |
|---|---|
| **Alta** | Bloquea una venta, pierde datos o es necesaria para la evaluación |
| **Media** | Molesta o confunde, pero hay forma de seguir trabajando |
| **Baja** | Estética o mejora |

| Clasificación | Significado |
|---|---|
| Error | El sistema hace algo incorrecto o pierde datos |
| Validación | Acepta un dato que debería rechazar, o rechaza uno válido |
| Usabilidad | Funciona, pero es lento, confuso o propenso a error para la cajera |
| Flujo | El orden de pasos no calza con cómo se trabaja en el local |
| Alcance | Falta una función o pantalla definida en las HU o el prototipo |
| Presentación | Formato de textos, montos o columnas |
| Mejora | No es falla: sugerencia |
| Configuración | Hardware o entorno, no código |
| Calidad de código | Pruebas, estilo; no afecta al usuario |

**Estados:** *Abierto* (falta corregir) · *Corregido* (el desarrollo lo corrigió y espera que QA lo vuelva a
probar) · *Cerrado* (QA lo volvió a probar y lo aprobó).

**Ciclo de vida:** QA reporta con evidencia → se asigna responsable → el desarrollador corrige y anota el
commit en `COMENTARIO DEV` → QA vuelve a probar en el «Ambiente QA 2» y marca *Aprobado*, *Aprobado con
observaciones* o *Rechazado* → si se rechaza, vuelve a *Abierto*.

## 2. Resumen por ciclo

| Ciclo | Fecha | Defectos reportados |
|---|---|---|
| Ciclo 1 · QA inicial (ramas `feature/ventas-caja-dominio` y `fix/pr3-conflictos-main`) | 26-10-2026 | 38 |
| Ciclo 2 · QA del 29-10 (15 casos Q-01 a Q-15 + hallazgos) | 29-10-2026 | 6 (+15 casos manuales Q-01 a Q-15) |
| Ciclo 3 · QA del 02-11 | 02-11-2026 | 11 |
| Ciclo 4 · QA del 04-11 | 04-11-2026 | 15 |
| Ciclo 5 · QA del 05-11 | 05-11-2026 | 14 |
| Ciclo 6 · QA del 09-11 (re-prueba de 38 hallazgos y 6 nuevos) | 09-11-2026 | 6 |

**Total de defectos registrados: 90** (en 7 módulos).

### 2.1 Estado actual

| Estado | Cantidad | % |
|---|---|---|
| Cerrado | 50 | 56 % |
| Corregido | 40 | 44 % |
| Abierto | 0 | 0 % |

### 2.2 Por prioridad

| Prioridad | Total | Abiertos |
|---|---|---|
| Alta | 27 | 0 |
| Media | 34 | 0 |
| Baja | 29 | 0 |

### 2.3 Por clasificación

| Clasificación | Cantidad |
|---|---|
| Usabilidad | 23 |
| Error | 21 |
| Alcance | 16 |
| Presentación | 8 |
| Mejora | 7 |
| Flujo | 6 |
| Validación | 5 |
| Calidad de código | 3 |
| Configuración | 1 |

### 2.4 Por módulo

| Módulo | Defectos | Abiertos |
|---|---|---|
| F1 Operación | 43 | 0 |
| F2 Catálogo | 16 | 0 |
| F3 Inventario | 6 | 0 |
| F4 Clientes | 4 | 0 |
| F5 Compras | 6 | 0 |
| F6 Reportes | 5 | 0 |
| F7 Administración | 10 | 0 |

### 2.5 Por responsable

| Responsable | Defectos | Abiertos |
|---|---|---|
| Fernando Silva | 70 | 0 |
| Eduardo Guzmán | 16 | 0 |
| Equipo | 2 | 0 |
| Victoria Roa | 1 | 0 |
| Por asignar | 1 | 0 |

## 3. Resultado de los ciclos

- **Ciclo 1 (26-10):** la primera revisión encontró 38 hallazgos en la venta, la caja y el catálogo.
- **Ciclo 2 (29-10):** se ejecutaron 15 casos manuales (`Q-01` a `Q-15`, ver `casos-de-prueba.md`).
- **Ciclos 3 a 5 (02, 04 y 05-11):** hallazgos de usabilidad y alcance sobre las pantallas F1 a F7.
- **Ciclo 6 (09-11):** QA volvió a probar 38 hallazgos: **30 aprobados**, 4 no aprobados (uno en forma
  parcial), 3 pendientes de revisión y 1 con una definición nueva de la Product Owner. Además registró 6
  hallazgos nuevos (O-37, O-38, O-39, CL-04, A-09, A-10).
- **10-11:** el desarrollo corrigió los 9 que le correspondían a Fernando (commits `4c44c7b` y `3876212`).
- **11-11:** Eduardo corrigió **R-05, A-09 y A-10** (commits `bd14e43` y `221c2eb`), integrados en `develop`.
  **No quedan defectos abiertos.** Los 40 en estado *Corregido* esperan la re-prueba de QA.
- El commit `bd14e43` corrige además CO-07, CO-08, CL-07 e I-07, hallazgos del 10-11 que todavía no
  están en este registro (falta traspasarlos desde la planilla de QA).

## 4. Defectos abiertos (pendientes)

Ninguno al 11-11-2026. Pendiente: re-prueba de QA de los 40 defectos en estado *Corregido*.

## 5. Detalle por módulo

Columnas: **Reportado** = fecha del ciclo en que se encontró · **Re-prueba QA** = resultado de la re-prueba en el Ambiente QA 2 · **Corrección** = lo que dejó anotado el desarrollo.

### F1 Operación (43)

| ID | Resumen | Clasif. | Prior. | Resp. | Reportado | Estado | Re-prueba QA | Corrección |
|---|---|---|---|---|---|---|---|---|
| O-00 | El lector lee el código correctamente pero no envía Enter al final de la lectura | Configuración | Alta | Equipo | 26-10-2026 | Cerrado | Aprobado | — |
| O-01a | La venta no se inicia sola: hay que apretar «Nueva venta» al abrir y después de cada cobro | Flujo | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): la venta se inicia sola al arrancar (si hay turno), al abrir turno y después de cada cobro. Se corrigió ad… |
| O-01b | «Nueva venta» reemplaza el ticket actual y descarta lo que tenía, sin confirmación | Alcance | Media | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 917182d (develop/integracion, 29-10, Fernando): varios tickets abiertos en pestañas (Ticket 1, Ticket 2…). «Nuevo ticket (Ins)» abre otra venta y la anterior qued… |
| O-01c | Mensaje escrito con voseo: «Primero iniciá una venta nueva» | Presentación | Baja | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): textos corregidos. Verificado 28-10: no quedan formas con voseo (iniciá, podés, tenés) en src/. |
| O-02 | Enter en el campo Código no agrega el producto; hay que apretar «Agregar» | Error | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): Enter en Código agrega el producto. Depende de B-01 (configurar sufijo Enter en el lector). |
| O-02B | Para agregar un producto hay que apretar Enter. Al escanear no se agrega solo, y un producto a granel se agrega sin pedir el peso | Flujo | Alta | Fernando | 02-11-2026 | Cerrado | Aprobado con Observaciones | — |
| O-03 | No hay forma de quitar un producto del ticket | Error | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): botón «Quitar línea» y tecla Supr sobre el ticket. |
| O-04 | Para cambiar la cantidad hay que volver a escanear | Mejora | Baja | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 1faa0c3 (develop/integracion, 29-10, Fernando): botones «+» y «−» y teclas + / − sobre la línea seleccionada; si la cantidad llegaría a 0 pregunta si quitar la lí… |
| O-05 | La columna Subtotal queda fuera de la ventana con el tamaño inicial | Presentación | Baja | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): ventana 980x680 (mínimo 900x620) y anchos de columna explícitos. |
| O-06 | La cantidad con coma («0,705») se rechaza; solo acepta punto | Validación | Media | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): acepta coma y punto como separador decimal. |
| O-07 | Los montos se muestran sin separador de miles («$26074») | Presentación | Media | Fernando | 26-10-2026 | Cerrado | Aprobado con Observaciones | Commit fc9813d (develop/integracion, 29-10, Fernando): función única de formato de montos (formatear_clp y parsear_monto en dominio/formato.py). F1 y los mensajes de err… |
| O-08 | El número grande es el total sin redondear; lo que se cobra («A cobrar») y el vuelto se ven en letra chica o en un mensaje que se cierra | Usabilidad | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): el número grande es «A cobrar» (redondeado si hay efectivo) y hay barra fija Total/Pagado/Vuelto. |
| O-09a | No se puede quitar ni corregir un pago ya agregado, y los pagos no se ven listados | Error | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): Venta.quitar_pago (dominio, con test), lista de pagos y botón para quitar uno. |
| O-10b | En pago mixto el efectivo debe ingresarse al final; un efectivo menor al total se rechaza | Flujo | Media | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): Venta.construir_pago_efectivo (dominio, con test): efectivo menor al saldo es pago parcial, sin redondeo n… |
| O-11 | Con tarjeta o transferencia hay que escribir el monto a mano | Mejora | Baja | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): el monto se sugiere con el saldo pendiente. |
| O-12 | Acepta decimales en productos que se venden por unidad (1.5 almendras = $5.985) | Validación | Media | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): rechaza cantidad decimal en productos por unidad; solo granel admite decimales (con test). |
| O-13 | El stock se valida al cerrar la venta y no al agregar el producto | Error | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): valida stock al agregar la línea; se mantiene también al cerrar. |
| O-14 | La cantidad no vuelve a 1 después de agregar un producto ni al iniciar venta | Error | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): la cantidad vuelve a 1 después de cada alta. |
| O-15 | Después de agregar un producto, el cursor no vuelve al campo Código | Usabilidad | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): el foco vuelve a Código tras cada alta y al abrir turno. |
| O-16 | Se acepta un pago con tarjeta mayor al total y después la venta no cierra, con un mensaje incorrecto | Error | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): rechaza al agregar un pago no-efectivo que supera el saldo pendiente (con test). |
| O-17 | No existe búsqueda de producto por nombre en la venta | Alcance | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit fc9813d (develop/integracion, 29-10, Fernando): atajo F10 «Buscar producto» (el botón lo indica). Falta probarlo con el lector real. |
| O-18 | El movimiento de caja se pide en tres ventanas sucesivas, con tipo escrito a mano y motivo en texto libre | Usabilidad | Media | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): diálogo único con Tipo, Motivo (lista de la PO del 22-09), Observación y Monto, con confirmación final. |
| O-19 | El arqueo calcula bien pero se presenta en un mensaje sin formato | Presentación | Baja | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit fc9813d (29-10, Fernando): la lista Pago de F1 ya muestra Efectivo, Tarjeta, Transferencia y Crédito cliente (antes efectivo / credito_cliente). El arqueo ya los… |
| O-20 | El cierre no pide conteo por billete y moneda; se escribe un solo número | Alcance | Media | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): apertura y cierre piden conteo por billete/moneda (ConteoDenominaciones). Sigue pendiente la validación de… |
| O-21 | No se pueden ver las ventas del día ni el total por medio de pago con el turno abierto | Alcance | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit fc9813d (develop/integracion, 29-10, Fernando): subpestañas Venta · Caja y corte · Resumen del día. Caja y corte agrupa abrir turno, movimiento de caja, cerrar tu… |
| O-22 | En el conteo por billete y moneda (abrir turno y arqueo), el 0 queda delante del número escrito: se ve «05» en vez de «5» | Presentación | Baja | Fernando | 29-10-2026 | Cerrado | Aprobado | Commit 1faa0c3 (develop/integracion, 29-10, Fernando): al entrar a la casilla del conteo se selecciona el contenido y lo escrito lo reemplaza (ya no queda «05»). |
| O-23 | No se ve cuánto efectivo hay en caja en este momento; solo se muestra el fondo inicial | Mejora | Media | Fernando | 29-10-2026 | Cerrado | Aprobado | Commit fc9813d (develop/integracion, 29-10, Fernando): «En caja: $X» en Caja y corte = fondo + efectivo entregado − vueltos + ingresos − retiros; se actualiza tras cada… |
| O-24 | Los ingresos y retiros de caja no se pueden consultar después de registrarlos | Alcance | Media | Fernando | 29-10-2026 | Cerrado | Aprobado | Commit fc9813d (develop/integracion, 29-10, Fernando): Caja y corte lista los movimientos del turno con hora, tipo, monto, motivo y usuario. |
| O-25 | Un ticket sin cobrar se pierde al cerrar la ventana | Alcance | Media | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 917182d (develop/integracion, 29-10, Fernando): los tickets con productos se guardan y se recuperan al reabrir (productos y lote elegido; los pagos no se guardan)… |
| O-26 | Acepta monto 0 en el pago | Validación | Baja | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit 514e7ab (feature/ventas-caja-dominio, 28-10, Fernando): rechaza montos <= 0 con mensaje claro. |
| O-27 | Con efectivo, «A cobrar» y el Monto propuesto muestran el total sin redondear. Por eso el pago exacto se rechaza ($15.296 pide $15.300) o se da un vu… | Error | Alta | Fernando | 26-10-2026 | Cerrado | Aprobado | Commit fc9813d (develop/integracion, 29-10, Fernando): con efectivo (medio por defecto) «A cobrar» y Monto muestran desde el inicio el total redondeado a la decena (15.2… |
| O-28 | La tecla F5 de «Cambiar lote» abre el módulo F5 Compras | Usabilidad | Media | Fernando | 02-11-2026 | Cerrado | Aprobado | — |
| O-29 | En el conteo por billete y moneda (abrir turno y cierre), Enter no confirma; hay que hacer clic en «Confirmar» | Mejora | Baja | Fernando | 02-11-2026 | Corregido | Pendiente | Corregido en 5550f1d (PR #10, 02-11): en los cuadros de conteo de billetes y monedas (abrir turno y cierre) Enter confirma y Esc cancela. Re-probar en la versión actual… |
| O-30 | Al cerrar la jornada con tickets sin cobrar, no avisa y los tickets se pierden | Flujo | Alta | Fernando | 02-11-2026 | Corregido | Pendiente | Corregido en f354c96 (PR #9, 02-11): los tickets en espera se conservan al cerrar la app; al cerrar la jornada con tickets sin cobrar avisa y pide confirmar antes de des… |
| O-31 | Con un producto desactivado, el aviso aparece recién después de escribir el peso | Usabilidad | Baja | Fernando | 04-11-2026 | Corregido | Pendiente (corregido el 10-11) | F10 marca «(desactivado)» y avisa al elegirlo, antes de pedir cantidad (commit 4c44c7b) |
| O-32 | Al elegir un producto a granel en F10 solo se copia el código; hay que apretar Agregar, escribir el peso y volver a Agregar | Flujo | Media | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d y 0a0b4f7 (05-11): en F10, si el producto es a granel el botón dice «A granel · pedir peso» y al aceptar se abre el cuadro del peso y entra al ticke… |
| O-33 | La nota de la venta (Ctrl+N) no se ve en ninguna pantalla de ventas; solo queda en F7 › Auditoría | Alcance | Baja | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d y 0a0b4f7 (05-11): la nota de la venta sale en el comprobante y en la tabla «Ventas del turno» de Caja y corte, junto a la hora, el total y el pago. |
| O-34 | «Venta de la jornada» muestra solo el turno abierto: con un segundo turno sale $0, aunque Resumen del día muestra las ventas | Usabilidad | Baja | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d (05-11): la tabla se llama «Venta del turno» (es la del turno abierto); el total del día completo está en Resumen del día. |
| O-35 | Un retiro de caja acepta el motivo «Ingreso de sencillo» | Error | Baja | Fernando | 04-11-2026 | Corregido | Pendiente (corregido el 10-11) | El ingreso de caja ofrece solo «Ingreso de sencillo» (commit 4c44c7b) |
| O-36 | Al «Agregar pago» en efectivo, la lista muestra solo el monto cobrado; «Pagó con» y «su cambio» vuelven a $0 y el vuelto no se muestra en ningún mome… | Error | Alta | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): el cobro muestra el cambio que se entrega («Pagó con» y «su cambio») al agregar el pago en efectivo. |
| O-37 | La columna Lote se ve desordenada («* 123 · vence 2026-11-13») | Presentación | Media | Fernando | 09-11-2026 | Corregido | Pendiente (corregido el 10-11) | Columna legible «L2 (vence 14-11) · elegido», fechas día-mes y columna más ancha (commits 4c44c7b, 3876212) |
| O-38 | La ventana de F10 corta el botón cuando hay muchos productos | Error | Media | Fernando | 09-11-2026 | Corregido | Pendiente (corregido el 10-11) | Ventana de alto fijo con barra de desplazamiento y botones siempre visibles (commit 4c44c7b) |
| O-39 | «Necesita atención» no dice qué producto no tiene costo | Usabilidad | Media | Fernando | 09-11-2026 | Corregido | Pendiente (corregido el 10-11) | El aviso nombra los productos y «Ver →» abre F2 filtrado «Sin costo» con un clic (commits 4c44c7b, 3876212) |

### F2 Catálogo (16)

| ID | Resumen | Clasif. | Prior. | Resp. | Reportado | Estado | Re-prueba QA | Corrección |
|---|---|---|---|---|---|---|---|---|
| CA-02 | El campo Categoría pide un número (ID) y no el nombre; si se escribe texto, se descarta sin aviso | Usabilidad | Alta | Victoria | 02-11-2026 | Cerrado | Aprobado | Commit anterior (develop, 29-10, Fernando): las categorías ya no están fijas en el código: hay una tabla categorias (la base nueva trae las 4 de siempre con sus ids), F2… |
| CA-04 | Se guarda un producto sin categoría y la tabla muestra «None» | Validación | Alta | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): el dominio rechaza un producto sin categoría y el formulario la exige. Verificado 28-10 con prueba directa. Ya… |
| CA-05a | Se guarda un producto perecible con «Días aviso» vacío | Validación | Media | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): un perecible sin días de aviso (o con 0) se rechaza en dominio y en pantalla. Verificado 28-10. |
| CA-05b | Perecible, Días aviso y Costo no se guardan en la base | Error | Alta | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): columnas costo_neto, perecible y dias_aviso en SQLite; se guardan y se recuperan al reabrir (verificado 28-10).… |
| CA-06 | Con costo 0 y precio 1000, el margen muestra 100 % | Error | Media | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): PARCIAL: con costo vacío muestra «falta costo» y el markup con costo 0 muestra «falta costo». Pero el MARGEN co… |
| CA-08a | La búsqueda distingue tildes: «Te» no encuentra «Té verde» | Error | Media | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): la búsqueda de la pantalla normaliza tildes y mayúsculas. Verificado 28-10: «te» encuentra «Té verde». Nota: el… |
| CA-08b | Hay que apretar el botón «Buscar»; Enter no busca | Mejora | Baja | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): Enter en el campo de búsqueda ejecuta la búsqueda. |
| CA-10 | No existe forma de editar un producto | Error | Alta | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): doble clic sobre la fila carga el producto real en el formulario (código bloqueado) y «Guardar cambios» lo actu… |
| CA-11 | El formulario no se limpia después de agregar un producto | Usabilidad | Media | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): el formulario se limpia y el cursor vuelve a Código después de agregar o editar. |
| CA-13 | Después de seleccionar un producto, el Código queda bloqueado con ese código; al cargar otro producto o escribir uno nuevo se mezclan datos y «Agrega… | Error | Alta | Eduardo | 29-10-2026 | Cerrado | Aprobado | Integrado en develop/integracion (merge 3388687, 29-10, Fernando) con el commit 09658ad de Eduardo, sin conflictos y con las pruebas en verde. Falta repetir el QA de Cat… |
| CA-14 | El campo Nombre es angosto y el texto se corta («Avena a granel (de…»). | Presentación | Baja | Eduardo | 02-11-2026 | Corregido | Rechazado | Integrado en develop/integracion (merge 3388687, 29-10, Fernando) con el commit 09658ad de Eduardo. Falta repetir el QA de Catálogo sobre develop. / 07-11: ficha de F2 c… |
| CA-15 | La búsqueda trae coincidencias en medio de una palabra: «te» trae Aceite y Pan integral | Usabilidad | Baja | Eduardo | 02-11-2026 | Corregido | Rechazado | Integrado en develop/integracion (merge 3388687, 29-10, Fernando) con el commit 09658ad de Eduardo. Falta repetir el QA de Catálogo sobre develop. / 07-11: F2 ordena pri… |
| CA-16 | No existe forma de crear, renombrar o desactivar categorías | Alcance | Alta | Eduardo | 02-11-2026 | Cerrado | Aprobado | — |
| CA-17 | Las categorías solo se pueden desactivar y activar; no se pueden eliminar | Alcance | Baja | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d (05-11): F2 › Categorías › «Eliminar», solo si no tiene productos (si los tiene pide fusionar o reasignar); queda en la auditoría. |
| CA-18 | Los desplegables de categoría solo se recorren con la flecha; no se puede escribir para buscar | Usabilidad | Media | Fernando | 04-11-2026 | Corregido | Pendiente (corregido el 10-11) | El desplegable muestra una lista que se acorta con cada letra (commit 4c44c7b) |
| CA-19 | El código de barras no se puede modificar en la ficha (aparece bloqueado) | Alcance | Media | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d (05-11): el código de barras se puede cambiar en la ficha; no se admite uno repetido, se actualiza en todas las tablas y en los tickets en espera, y… |

### F3 Inventario (6)

| ID | Resumen | Clasif. | Prior. | Resp. | Reportado | Estado | Re-prueba QA | Corrección |
|---|---|---|---|---|---|---|---|---|
| I-01 | No hay pantalla para ingresar stock de un producto nuevo | Alcance | Alta | Por | 26-10-2026 | Cerrado | Aprobado | Commit c7f5ccd (develop/integracion, 28-10, Fernando): F3 Inventario permite ingresar stock con cantidad, motivo y vencimiento (el perecible exige fecha; un lote ya venc… |
| I-02 | El lote se identifica con un número automático («L1») y no con el código impreso en el envase | Alcance | Media | Fernando | 02-11-2026 | Cerrado | Aprobado con Observaciones | — |
| I-03 | Si falta un dato (por ejemplo, la cantidad), «Ingresar» no hace nada y no dice qué falta | Usabilidad | Media | Fernando | 02-11-2026 | Cerrado | Aprobado | — |
| I-04 | La tecla Insert no abre «Agregar a inventario», aunque el botón dice «INS» | Error | Baja | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): la tecla Insert abre «Agregar a inventario» en F3, igual que en F2 y F5. |
| I-05 | Al cerrar el cuadro y volver a abrirlo, queda escrito el código anterior | Usabilidad | Baja | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): el cuadro «Agregar a inventario» se abre vacío, también después de «Ingresar». |
| I-06 | La columna Cantidad queda pegada a Motivo y se confunden | Usabilidad | Baja | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): la columna Cantidad queda separada de Motivo en el reporte de movimientos. |

### F4 Clientes (4)

| ID | Resumen | Clasif. | Prior. | Resp. | Reportado | Estado | Re-prueba QA | Corrección |
|---|---|---|---|---|---|---|---|---|
| CL-01 | El cliente no tiene cupo de crédito | Alcance | Media | Fernando | 04-11-2026 | Corregido | Pendiente (corregido el 10-11) | Cupo de crédito por cliente: formulario, lista, Cuenta y bloqueo en F1; migración 009 (commit 4c44c7b) |
| CL-02 | El estado de cuenta muestra «Venta N° 1 · 1 producto», sin decir qué producto | Alcance | Media | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d y 0a0b4f7 (05-11): cada consumo lista sus productos con cantidad y monto, en las pestañas Estado de cuenta y Cuenta. |
| CL-03 | El descuento del crédito familiar y el total a pagar dicen «por confirmar» | Error | Alta | Fernando | 04-11-2026 | Corregido | Pendiente (corregido el 10-11) | Estado de cuenta con consumos, descuento del 20 % en pesos y total a pagar (commit 4c44c7b) |
| CL-04 | La pestaña Cuenta no permite elegir el cliente | Usabilidad | Media | Fernando | 09-11-2026 | Corregido | Pendiente (corregido el 10-11) | Selector de cliente con búsqueda en Cuenta y Estado de cuenta; ciclo actual por defecto (commit 4c44c7b) |

### F5 Compras (6)

| ID | Resumen | Clasif. | Prior. | Resp. | Reportado | Estado | Re-prueba QA | Corrección |
|---|---|---|---|---|---|---|---|---|
| CO-01 | Si el producto es nuevo, la factura dice «No existe un producto con código…» y hay que ir a F2 a crear la ficha | Flujo | Alta | Fernando | 05-11-2026 | Corregido | Pendiente | — |
| CO-02 | No se pueden editar los datos de un proveedor | Alcance | Baja | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): botón «Editar proveedor» para cambiar nombre y contacto, con validación de nombre repetido y registro en la auditoría. |
| CO-03 | Al crear un proveedor con «Nuevo proveedor», la pantalla salta a la pestaña Proveedores y cambia el proveedor de la factura en curso | Usabilidad | Media | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): al crear un proveedor desde «Nuevo proveedor» la pantalla se queda en «Registrar factura» con las líneas visibles. |
| CO-04 | No queda claro que falta apretar «Confirmar factura»; al salir sin confirmar no se guarda nada y no hay aviso | Usabilidad | Media | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): «Confirmar factura» queda como botón principal, avisa «Hay una factura sin confirmar» al cambiar de pestaña, de módulo o salir, y al confir… |
| CO-05 | La cantidad no indica la unidad y no acepta «1k» | Usabilidad | Media | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): junto a la cantidad se muestra la unidad del producto («kg» si es a granel, «unid.» si no). |
| CO-06 | Una línea agregada no se puede editar; solo quitarla | Usabilidad | Media | Fernando | 05-11-2026 | Corregido | Pendiente | Corregido en 0a0b4f7 (05-11): doble clic en una línea carga sus datos en el formulario para corregirla. |

### F6 Reportes (5)

| ID | Resumen | Clasif. | Prior. | Resp. | Reportado | Estado | Re-prueba QA | Corrección |
|---|---|---|---|---|---|---|---|---|
| R-01 | Las fechas Desde y Hasta se escriben a mano en formato AAAA-MM-DD | Mejora | Baja | Eduardo | 29-10-2026 | Cerrado | Aprobado | Commit anterior (develop, 29-10, Fernando): las fechas Desde y Hasta de F6 y el campo Vence de F3 tienen calendario desplegable (clic en el campo o en el botón ▾; tambié… |
| R-02 | El reporte muestra «Categoria 3» en vez del nombre y «credito_cliente» como medio de pago. En el equipo de QA no generó resultados | Error | Media | Fernando | 02-11-2026 | Corregido | Pendiente | Corregido en 5550f1d (PR #10, 02-11): el reporte muestra el nombre de la categoría y «Crédito cliente» en vez de los códigos internos. Re-probar en feat/diseno-prototipo… |
| R-03 | En «Configurar meta diaria» el 0 queda delante de lo que se escribe | Usabilidad | Baja | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d (05-11): un campo que ya trae un número queda seleccionado al entrar, así lo que se escribe lo reemplaza. |
| R-04 | El estado «Inactivo» se ve igual que «Activo» | Usabilidad | Baja | Fernando | 05-11-2026 | Corregido | Pendiente | — |
| R-05 | Desde Rotación se puede desactivar productos, pero no reactivarlos | Usabilidad | Baja | Fernando | 05-11-2026 | Corregido | Pendiente (corregido el 11-11) | Corregido en bd14e43 (11-11, Eduardo): «Reactivar» aparece en lugar de «Desactivar» al filtrar Inactivos |

### F7 Administración (10)

| ID | Resumen | Clasif. | Prior. | Resp. | Reportado | Estado | Re-prueba QA | Corrección |
|---|---|---|---|---|---|---|---|---|
| GEN-01 | La interfaz no sigue el prototipo navegable v2: hay dos ventanas separadas (Productos y Ventas) en ramas distintas | Alcance | Alta | Equipo | 26-10-2026 | Cerrado | Aprobado | — |
| A-02 | Ruff reporta 5 observaciones en la rama fix/pr3-conflictos-main | Calidad de código | Baja | Eduardo | 26-10-2026 | Cerrado | Aprobado | Commit 1a6a143 (fix/pr3-conflictos-main, 28-10, Eduardo): líneas largas acortadas y MotivoAjuste hereda de StrEnum. Verificado 28-10: ruff «All checks passed!» y 86 prue… |
| A-03 | Al abrir el sistema con login la ventana queda en negro y no aparece el cuadro para crear la contraseña ni para iniciar sesión | Error | Alta | Fernando | 29-10-2026 | Cerrado | Aprobado | Commits fc9813d y a0bd906 (develop, 29-10, Fernando): la ventana principal ya no se oculta durante el acceso (se tapa con una cubierta lisa) y el cuadro se muestra al fr… |
| A-04 | En Windows falla test_catalogo_gui: la prueba imprime «−» (U+2212) y la consola cp1252 da UnicodeEncodeError | Calidad de código | Baja | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en 3e03213 (03-11): los escenarios de prueba fuerzan UTF-8 en la salida, así que el «−» ya no rompe la consola cp1252 de Windows. |
| A-05 | Sin POS_TEST_PG_URL, el fixture pg() de test_sync_postgres_pantallas hace None.lower() y da 5 errores | Calidad de código | Baja | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en 3e03213 (03-11): sin POS_TEST_PG_URL las pruebas de Postgres se omiten en vez de fallar. |
| A-06 | El cierre por inactividad bloquea la sesión, pero tarda más que el tiempo configurado | Error | Media | Fernando | 04-11-2026 | Corregido | Pendiente | Corregido en b25037d (05-11): el movimiento del mouse ya no cuenta como actividad y el cierre de sesión llega al vencer el plazo configurado. |
| A-07 | Las tablas no tienen líneas entre filas ni columnas y cuesta seguir una fila | Usabilidad | Media | Fernando | 05-11-2026 | Corregido | Pendiente | — |
| A-08 | En los calendarios, el día de hoy solo se marca con un punto | Mejora | Baja | Fernando | 05-11-2026 | Corregido | Pendiente | — |
| A-09 | Centrar los datos de las tablas | Presentación | Baja | Eduardo | 09-11-2026 | Corregido | Pendiente (corregido el 11-11) | Corregido en bd14e43 (11-11, Eduardo): datos centrados salvo producto, código, categoría y función |
| A-10 | El calendario queda flotando al cambiar de módulo | Error | Media | Eduardo | 09-11-2026 | Corregido | Pendiente (corregido el 11-11) | Corregido en bd14e43 y 221c2eb (11-11, Eduardo): el calendario se cierra al perder el foco o cambiar de módulo |

## 6. Lecciones de los ciclos

- Casi todo lo que QA encontró fue de **usabilidad y alcance** (39 de 90), no de datos: la lógica de
  negocio estaba cubierta por pruebas automáticas y las fallas aparecieron al usar las pantallas reales.
  Por eso se agregaron escenarios de interfaz con la app real (`tests/e2e/`).
- Cada hallazgo corregido quedó **con su prueba**: ver la trazabilidad en `casos-de-prueba.md`.
- Los hallazgos nuevos del 09-11 salieron de **probar con ventas reales** (crédito, cupo, lotes); ese
  tipo de prueba se repite antes de cada entrega.
