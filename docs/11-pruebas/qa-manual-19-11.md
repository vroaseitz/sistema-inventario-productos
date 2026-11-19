# Pruebas manuales QA 19-11 — Emporio NaturalSur

**Para:** Victoria Roa (PO/QA) · **Rama:** `fix/qa-18-11` · **Fecha:** 19-11-2026

Verifica con la app real los cambios hechos a partir del QA del 18-11. Cada caso dice qué hacer, con qué datos y qué cifra debe verse. Marca **Pasa** o **Falla** y anota lo que veas. Si algo falla, mira la lista final «Qué mirar si algo falla».

## Resumen

| Cambio | Qué se prueba | Casos | Dónde |
|---|---|---|---|
| SY-01 | «Hacer corte de hoy» envía a la nube; avisos; límite de 45 s | QM-01, QM-31 a QM-34 | Local (QM-01) e internet |
| A-12 | Comprobantes con nombre único | QM-02 | Local |
| A-11 | Botón «Registrar factura» destacado en F5 | QM-03 | Local |
| CL-08 | Estado de cuenta: «Falta pagar» | QM-04, QM-05, QM-30 | Local |
| CL-06 | Anular venta pagada: efectivo / saldo a favor / cambio | QM-06 a QM-12 | Local |
| O-42 | Descuento por vencimiento 20 % a 14 días y 50 % a 7, editable | QM-13 a QM-18 | Local |
| CA-21 | IABA 10 % / 18 %, margen y F5 | QM-19 a QM-23 | Local |
| CA-22 | Botón «Eliminar» en la ficha | QM-24 a QM-26, QM-29 | Local |
| Migración | `scripts/importar_migracion.py` | QM-27 a QM-30, QM-34 a QM-36 | Local e internet |
| Revisión independiente 19-11 | Saldo a favor, rechazadas, tandas, reembolso por terminal | QM-37 a QM-40 | Local e internet |

## Cómo preparar los datos

Hay que tener el proyecto abierto en la Terminal, en la carpeta `capstone`. Datos ficticios, sin Supabase.

1. Doble clic en `demo/reiniciar_demo.command` (o `PYTHONPATH=src .venv/bin/python demo/preparar_demo.py`). Deja la base como nueva **el mismo día de la prueba**: usuaria `admin` / `admin-demo-2026`, proveedor «Frutos del Sur», cliente **Juan Pérez** (cupo $20.000), productos `ALM-GR` (Almendras a granel, $14.990/kg, perecible, aviso 45 días, sin stock) y `MIX-250` (Mix, $3.990, stock 20), y jornada abierta con **$50.000**.
2. Doble clic en `demo/abrir_demo.command` para abrir la app (sin Supabase).
3. Repite el paso 1 cuando un bloque diga «con la demo recién reiniciada» (cierra la app antes).
4. Cliente extra para CL-06: F4 → Nuevo cliente → **Ana Soto**, teléfono `+56 9 8765 4321`, sin cupo.
5. Los comprobantes se guardan en `demo/comprobantes/` (no hay impresora configurada).

**Vender en efectivo** (se usa en varios casos): F1 → escribe `MIX-250` + Enter → F12 Cobrar → Efectivo → entrega $5.000 → cobrar. Total $3.990, vuelto $1.010.

## Pruebas locales (sin internet)

### SY-01, A-12 y A-11

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-01 | Demo recién reiniciada. F1 → Caja y corte → **Hacer corte de hoy** → cuenta $50.000 (2×$20.000 + 1×$10.000) | Sale el «Arqueo de cierre» con diferencia $0. **No** aparece «Datos enviados a la nube» ni error. La barra dice «Pendientes: N (sin Supabase configurado)» | | |
| QM-02 | Con la jornada abierta, haz 2 ventas en efectivo seguidas (MIX-250 ×1 cada una) y cóbralas con «cobrar e imprimir». Abre `demo/comprobantes/` | Hay **2 archivos distintos**: `comprobante-AAAAMMDD-HHMMSS-…-00001.txt` y `…-00002.txt`. Ninguno pisó al otro | | |
| QM-03 | F5 Compras, mira la barra de botones | **Registrar factura** tiene el estilo destacado (relleno del color de F5), igual que «Nuevo producto» en F2 | | |

### CL-08: Estado de cuenta (cliente Juan Pérez)

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-04 | Demo reiniciada. F1: 2×`MIX-250` a **Crédito** de Juan ($7.980). F4 → Cuenta → Registrar abono $5.000, transferencia. Pestaña **Estado de cuenta** (Juan, ciclo actual) | Total de consumos $7.980 · Descuento del 20 % **− $1.596** · Abonos y saldo a favor **− $5.000** · **Falta pagar $1.384** · Saldo final $2.980. Ya no existe la línea «Total a pagar» | | |
| QM-05 | Sigue de QM-04: Registrar pago del estado de cuenta | Mensaje «Pago del estado de cuenta registrado». Falta pagar y deuda quedan en $0 | | |

### CL-06: anular una venta pagada

Antes de cada caso: demo reiniciada. Ruta: F1 → **Caja y corte** → **Anular venta** → elige la venta → motivo «Producto en mal estado» → elige opción → **Anular venta** → Sí. Solo la administradora puede anular.

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-06 | Vende 1 Mix en efectivo **sin cliente**. Abre «Anular venta» y elige esa venta | Aparecen las 3 opciones: «Devolución en efectivo», «Saldo a favor del cliente», «Cambio por otro producto». **Saldo a favor está gris** (no hay cliente); queda marcada la devolución en efectivo | | |
| QM-07 | Anula la venta de QM-06 con **Devolución en efectivo** | «La venta N° X quedó anulada». En «Movimientos del turno» hay un **Retiro** «Devolución · venta N° X» por **$3.990** | | |
| QM-08 | Sigue de QM-07: **Hacer corte de hoy**, cuenta $50.000 | Arqueo: «Ventas anuladas: 1 por $3.990», **Efectivo esperado $50.000** (50.000 + 5.000 entregados − 3.990 retiro − 1.010 vuelto), diferencia $0. No se descuenta dos veces | | |
| QM-09 | Vende 1 Mix en efectivo eligiendo cliente **Ana Soto**. Anula con **Saldo a favor del cliente** | Anulada. **No** hay retiro de caja. F4: Ana aparece con **A favor $3.990** (lista y pestaña Cuenta); su cuenta muestra un movimiento «Saldo a favor» | | |
| QM-10 | Sigue de QM-09: **Hacer corte de hoy** | Efectivo esperado **$53.990** (50.000 + 5.000 − 1.010 vuelto; el dinero sigue en la gaveta) | | |
| QM-11 | Vende 1 Mix en efectivo sin cliente. Anula con **Cambio por otro producto** | Anulada. Retiro «Devolución por cambio · venta N° X» por $3.990. Se abre una **venta nueva vacía** en F1 lista para agregar el reemplazo | | |
| QM-12 | Vende 2×Mix a **Crédito** de Juan ($7.980). Anula esa venta | Las 3 opciones salen grises y el aviso dice «No hay dinero que devolver por caja (pago a crédito, tarjeta o transferencia)». Se anula igual; la deuda de Juan vuelve a $0; no hay retiro | | |

### O-42: descuento por vencimiento

Preparación: F3 → **Agregar a inventario** → 3 ingresos de `ALM-GR`, 5 kg cada uno, con código de lote y fecha «Vence» (usa el calendario): **L7** vence hoy + 7 días · **L14** hoy + 14 · **L15** hoy + 15.

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-13 | F3 → pestaña **Alertas** | L7: **50 %**, precio sugerido **$7.495** · L14: **20 %**, **$11.992** · L15: aparece en la lista (aviso a 45 días) pero **sin descuento**, $14.990. Ordenadas por días | | |
| QM-14 | F1: escribe `ALM-GR` + Enter, peso `0,350` | Franja «Descuento sugerido 50 % · Almendras a granel vence el DD-MM (el de L7) · F9 para aplicarlo». F9 abre el descuento a la línea | | |
| QM-15 | F2 → doble clic en Almendras. En «Descuento al acercarse el vencimiento»: Primera etapa **20** días, **10** %; Etapa final **3** días, **60** % → Guardar. F3 → Alertas | L7: **10 %**, **$13.491** · L14: 10 %, $13.491 · L15: 10 %, $13.491 | | |
| QM-16 | Abre de nuevo la ficha y deja las 4 casillas vacías → Guardar. Alertas | Vuelve a lo de QM-13 (50 % / 20 % / sin descuento). El texto de la ficha dice «Vacío = política por defecto: 20 % desde 14 días y 50 % desde 7 días» | | |
| QM-17 | En la ficha: Primera etapa **5** días (final queda en el valor por defecto, 7) → Guardar | No guarda. Aviso: «La etapa final del descuento debe empezar más cerca del vencimiento» | | |
| QM-18 | En la ficha: porcentaje `150` → Guardar; luego `abc` en días → Guardar | `150`: «El porcentaje de descuento debe estar entre 1 y 100». `abc`: «El descuento por vencimiento lleva solo números enteros.» | | |

### CA-21: IABA

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-19 | F2 → Nuevo producto: código `COLA1`, nombre «Bebida cola 1,5 L», categoría «Líquidos», costo neto `1.000`, precio `2.380`. IABA «No afecto» | IABA por unidad «—» · IVA $380 · Ganancia **$1.000**, Margen **50,0%**, Markup **100,0%** | | |
| QM-20 | Mismo formulario: IABA **18 %** | IABA por unidad **$180** · Ganancia **$820** · Margen **41,0%** · Markup **69,5%** (el margen cuenta neto + IABA, no el IVA) | | |
| QM-21 | IABA **10 %** | IABA por unidad **$100** · Ganancia **$900** · Margen **45,0%** · Markup **81,8%** | | |
| QM-22 | Deja 18 % y Guarda. Reabre la ficha de `COLA1` | Se reabre con «18 %», IABA $180 y margen 41,0% | | |
| QM-23 | F5 → Registrar factura: proveedor Frutos del Sur, N° `70001`, línea `COLA1`, cantidad `10`, costo unitario neto `1.000` → Agregar línea | Neto $10.000 · IVA $1.900 · Total $11.900 y, aparte, **«IABA (aparte del IVA): $1.800»**. El total no suma el IABA | | |

### CA-22: Eliminar producto

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-24 | F2 → Nuevo producto: `ERROR1`, «Creado por error», categoría «Líquidos», precio `1.000` → Guardar. Doble clic en él → **Eliminar** → Sí | Pregunta «¿Eliminar «Creado por error»? … no se puede deshacer». Luego «Producto Creado por error eliminado.» y desaparece de la lista. F7 → Auditoría: «Eliminación de producto» | | |
| QM-25 | Doble clic en `MIX-250` (tiene stock) → **Eliminar** | **No elimina**. Dice que tiene ventas, lotes, facturas o movimientos y pregunta «¿Quieres desactivarlo?». Responder **Sí** lo deja desactivado y «No» no cambia nada | | |
| QM-26 | Doble clic en `COLA1` (ya tiene factura de QM-23) → **Eliminar** | Mismo aviso que QM-25 (no se elimina; ofrece desactivar). En la ficha de un producto **nuevo** (aún sin guardar) no hay botón Eliminar | | |

### Migración de datos (ensayo local)

Guía: `docs/12-despliegue/migracion-de-datos.md`. Cierra la app. Crea una carpeta con estos 2 archivos (separador `;`, UTF-8):

`productos.csv`: `codigo;nombre;unidad_venta;categoria;precio_venta_con_iva;costo_neto;iva;impuesto_adicional;existencia;stock_minimo`, y las filas `BEB1;Bebida cola 1,5 L;unidad;Líquidos;2380;1000;190;0;24;` · `PAN1;Pan amasado;unidad;Panadería y repostería;1500;600;114;0;10;` · `GRA1;Almendras a granel;granel;Frutos secos y semillas;14990;8000;1520;0;2,5;` · `MER1;Mermelada artesanal;unidad;Aceites, untables y endulzantes;5565;2500;475;0;10;` · `FUDGE;;unidad;Sin categoría;990;;;;0;` · `7700000000001;;unidad;Líquidos;1000;500;95;0;1;`

`clientes.csv`: `nombre;telefono;observaciones;cupo;deuda_actual;ultimo_pago`, y las filas `Cliente Credito;;vecino;50000;12000;2026-10-02` · `Cliente Cero;;;20000;0;` · `;;;1000;0;`

Comando base (desde `capstone`): `PYTHONPATH=src POS_SQLITE_PATH="$PWD/demo/demo.db" .venv/bin/python scripts/importar_migracion.py --productos productos.csv --clientes clientes.csv`

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-27 | Demo reiniciada. Comando con `--simulacro` al final. Luego abre la app | Dice «SIMULACRO, nada se guardó». «Productos: 6 leídos, 5 cargados, … 1 rechazados» (rechaza `7700000000001`: sin nombre). «Clientes: 3 leídos, 2 cargados» (rechaza el sin nombre). La app **no** tiene ninguno de los productos nuevos | | |
| QM-28 | Cierra la app. Corre el comando **sin** `--simulacro`; luego **otra vez** | 1.ª vez: «guardado», mismos números. 2.ª vez: «0 cargados, 5 ya existían» (productos); nada se duplica | | |
| QM-29 | Abre la app. F2: busca `FUDGE` y `GRA1`. F3 → Reporte de movimientos: `BEB1`. F4: `Cliente Credito` | F2 muestra 7 productos (2 de la demo + 5). `FUDGE` se llama «FUDGE»; `GRA1` es a granel con 2,5 kg. `BEB1`: movimiento «Carga inicial» de 24. `Cliente Credito`: cupo $50.000, deuda **$12.000** («Saldo anterior»), teléfono «Sin teléfono (migración)». Se puede eliminar `FUDGE` (sin historia) pero no `PAN1` (CA-22) | | |
| QM-30 | Con lo de QM-29 (jornada abierta): F1: 2×`MER1` a **Crédito** de Cliente Credito ($11.130). F4: abono $5.000 transferencia. Estado de cuenta de Cliente Credito | Consumos **$23.130** (12.000 heredados + 11.130) · Descuento **− $4.626** · Abonos y saldo a favor **− $5.000** · **Falta pagar $13.504** · Saldo anterior $0 · **Saldo final $18.130**. La deuda heredada se fecha el día del corte y sí recibe el 20 % (Germaine, 19-11) | | |

## Pruebas que necesitan internet/Supabase real (PC del local)

Requisitos: `SUPABASE_DB_URL` configurada, migraciones 009 y 010 aplicadas en Supabase (`database/migraciones/010_pegar_en_sql_editor.sql.txt`) y `scripts/verificar_supabase.py` sin errores. Usa una base de ensayo, no la del local en producción.

| ID | Pasos y datos | Resultado esperado | Resultado | Observaciones |
|---|---|---|---|---|
| QM-31 | Con internet y ventas pendientes: **Hacer corte de hoy** | Primero el arqueo. La barra dice «Sincronizando con la nube…». Luego el aviso «Cierre de jornada»: **«Jornada cerrada. Datos enviados a la nube.»** La barra queda en «Todo sincronizado» | | |
| QM-32 | Apaga el Wi-Fi, haz una venta, **Hacer corte de hoy** | La jornada **queda cerrada igual**. Aviso: **«Jornada cerrada. Quedan N operaciones sin enviar; se enviarán en el próximo cierre o con el botón Sincronizar.»** (N = lo que dice «Pendientes» en la barra). La app no se queda congelada | | |
| QM-33 | Sigue de QM-32: enciende el Wi-Fi y pulsa **Sincronizar** | Se envía todo; la barra queda en «Todo sincronizado»; sin avisos de error | | |
| QM-34 | Tras migrar (QM-28) en la base de ensayo, con ~3.400 operaciones pendientes: **Hacer corte de hoy** y cronometra | El cierre envía durante unos **45 s** y termina con «Quedan N operaciones sin enviar…» con N menor que al inicio. Repite el corte o pulsa **Sincronizar** hasta «Todo sincronizado» | | |
| QM-35 | Migración con producto de precio $0 (agrega la fila `CERO1;Sin precio;unidad;Sin categoría;0;;;;0;`) y **Sincronizar** | La nube lo acepta (migración 010); la cola no se detiene en ese producto | | |
| QM-36 | Elimina un producto sin historia (QM-24) y **Sincronizar** | Sin error. En Supabase el producto ya no existe (el borrado solo se aplica si no tiene historia allá) | | |
| QM-37 | F1: venta en efectivo de $3.000 a un cliente (Ana) → **Anular venta** → «Saldo a favor del cliente». F4 → Estado de cuenta de Ana → **Registrar pago del estado de cuenta** | La cuenta dice «A favor $3.000». El estado de cuenta muestra «Abonos y saldo a favor − $3.000». Registrar el pago **no da error** (revisión del 19-11) | | |
| QM-38 | Con internet y la migración 010 aplicada, sincroniza una base con un dato que la nube rechaza (lo prepara Fernando) | La sincronización **sigue**: la barra dice «… · N rechazadas por la nube»; el cierre avisa «La nube rechazó N operaciones… quedaron guardadas en este computador». Nada se pierde | | |
| QM-39 | Tras migrar (~3.400 pendientes), pulsa **Sincronizar** | Envía por tandas de 2 minutos: aviso «Se enviaron N operaciones y quedan M. Presiona «Sincronizar» otra vez para seguir.» | | |
| QM-40 | Anula una venta pagada **solo con tarjeta** (sin cliente). F7 → Auditoría | Queda la fila «Reembolso pendiente por tarjeta o transferencia» con el monto (se devuelve por el terminal, no desde la caja) | | |

## Qué mirar si algo falla

- **No aparece ningún aviso de nube al cortar:** la app se abrió sin `SUPABASE_DB_URL` (así funciona la demo); es lo esperado en QM-01. En el PC del local revisa la variable.
- **Cifras distintas en descuentos o «Falta pagar»:** revisa que las fechas de vencimiento sean hoy + N días exactos y que el ciclo del Estado de cuenta sea el mes actual.
- **Falta una opción al anular:** si la venta fue a crédito no hay dinero que devolver; «Saldo a favor» solo existe si la venta tiene cliente.
- **Efectivo esperado raro en el corte:** mira «Movimientos del turno» (¿hay retiro «Devolución»?) y que el pago entregado y el vuelto sean los de los casos.
- **Comprobantes:** si hay impresora configurada no se crean archivos; revisa `demo/comprobantes/` solo en la demo.
- **El importador no carga nada:** ¿cerraste la app? ¿`POS_SQLITE_PATH` apunta a la base correcta? Un código o nombre ya existente se omite (no actualiza).
- **Sincronización lenta o cortada:** conexión, migraciones 009/010 en Supabase, y `scripts/verificar_supabase.py`. Lo pendiente nunca se pierde.
- Anota siempre: ID del caso, pasos, lo que viste (captura) y la hora; el registro va en `registro-de-defectos.md`.
