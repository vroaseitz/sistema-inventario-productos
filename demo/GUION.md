# Guion de la presentación del 13-11 — Fernando

**Me toca:** lámina 4, lámina 5 y la demostración en vivo. **Tiempo total mío: unos 6 minutos.**
Presentación online, después del primer grupo.

| Momento | Quién | Tiempo |
|---|---|---|
| Láminas 1, 2 y 3 | Victoria | 2:30 |
| **Lámina 4 · Stack** | **Fernando** | **0:45** |
| **Lámina 5 · Arquitectura** | **Fernando** | **1:00** |
| Láminas 6 y 7 | Eduardo | 1:30 |
| **Demostración en vivo** | **Fernando** | **4:00** |

---

## Hoja de ruta (para tener a la vista mientras presento)

```
LÁMINA 4   Windows 8.1 manda → Python 3.11 → PyInstaller → SQLite + Supabase
LÁMINA 5   Capas → vende sin internet → cola sin duplicar → migración pendiente → "le paso a Eduardo"

DEMO  1  F5  factura 45678 · 42500 · 8075 · ALM-GR 5 × 8500 · L2024-001 · 7 dic   → costo 7.900 → 8.500
      2  F3  Alertas: 5 kg · 10 % de descuento sugerido                            → $13.491
      3  F1  (jornada ya abierta, $50.000) ALM-GR 0,350 · dcto 15 % · paga 20.000   → $4.460 · vuelto $15.540
      4  F1  Juan Pérez · MIX-250 ×2 · Crédito   → $7.980
         F4  abono 5000 · Estado de cuenta       → a pagar $6.384 · saldo $2.980
      5  F6  2 ventas $12.440 · margen 29,5 %    F7 Auditoría
CIERRE     "de punta a punta y sin internet" → Victoria
```

---

## Datos de acceso y de la demo

Son datos **ficticios**, solo para la base de demostración (`demo/demo.db`). No sirven en el local.

| Dato | Valor |
|---|---|
| Usuario | `admin` |
| Contraseña | `admin-demo-2026` |
| Perfil | Administradora |
| Base de datos | `demo/demo.db` (SQLite, sin Supabase) |
| Proveedor ya creado | Frutos del Sur |
| Cliente ya creado | Juan Pérez · +56 9 1234 5678 · cupo $20.000 |
| Jornada de caja | **ya abierta**, con $50.000 de fondo (2 × $20.000 + 1 × $10.000) |
| Producto a granel | `ALM-GR` · Almendras a granel · $14.990/kg · costo $7.900 |
| Producto por unidad | `MIX-250` · Mix de frutos secos 250 g · $3.990 · stock 20 |
| Factura | N° `45678` · neto `42500` · impuestos `8075` |
| Lote | `L2024-001` · vence 07-12-2026 |

Si el doble clic no funciona, desde la Terminal:

```bash
cd ~/dev/estudio/capstone
PYTHONPATH=src .venv/bin/python demo/preparar_demo.py        # deja la base como nueva
PYTHONPATH=src POS_SQLITE_PATH="$PWD/demo/demo.db" SUPABASE_DB_URL= .venv/bin/python -m pos   # abre la app
```

---

## Preparación (10 minutos antes)

- [ ] Doble clic en `demo/reiniciar_demo.command` (deja la base como nueva y **abre la jornada**).
      Hacerlo **el mismo día** de la presentación, para que la jornada sea de ese día.
- [ ] Doble clic en `demo/abrir_demo.command` (abre la app). Si el cuadro de ingreso se ve negro, un clic dentro.
- [ ] Entrar con `admin` / `admin-demo-2026`. Dejar la app en **F1 Operación**: abajo debe decir
      «Turno #1 abierto - fondo inicial $50.000».
- [ ] Cerrar WhatsApp, correo y notificaciones (modo No molestar).
- [ ] PPT abierto en la lámina 9 (capturas) y el video de 4 minutos a mano, por si falla algo.
- [ ] Este guion abierto en el celular o en otra pantalla.
- [ ] Al compartir: **pantalla completa**, no solo la ventana. Los cuadros de peso, cobro y calendario
      son ventanas aparte y no se verían.

---

## Lámina 4 · Stack tecnológico — 45 segundos

**Idea central:** no elegimos el stack por gusto; lo definió el computador del local.

> «Gracias, Victoria. El stack no lo elegimos por gusto: lo definió una restricción.
> El computador del local tiene **Windows 8.1**, que ya no tiene soporte, y el sistema tiene que
> funcionar ahí.
>
> Por eso usamos **Python 3.11**, que es la última versión compatible con ese Windows, y **Tkinter**
> para la interfaz, que viene incluido.
>
> **Docker no corre** en ese equipo, así que entregamos un ejecutable hecho con **PyInstaller**, con
> autorización de la docente.
>
> Los datos se guardan en **SQLite** dentro del computador, y **Supabase** es la copia en la nube.
> Y para la calidad: pytest, ruff y GitHub Actions.»

## Lámina 5 · Arquitectura e integración — 1 minuto

**Idea central:** el local nunca deja de vender, aunque se caiga internet.

> «La aplicación está armada en **tres capas**: la interfaz, los casos de uso y el dominio.
> El dominio tiene las reglas del negocio —cómo se calcula un margen, cuándo se rechaza un crédito— y
> no depende ni de la pantalla ni de la base de datos. Eso nos permite probarlo por separado.
>
> Lo más importante para el local: la aplicación trabaja sobre la base **local**. Si se cae internet,
> **se sigue vendiendo** igual.
>
> Cada operación queda en una **cola** con un identificador único. Cuando vuelve la conexión, la cola
> se publica en Supabase, y si un envío se corta a la mitad y se repite, **no se duplica**.
>
> Lo que todavía no implementamos es la **migración** de los datos del sistema antiguo; es un proceso
> aparte.
>
> Le paso a Eduardo, que les muestra los resultados de las pruebas.»

*(Eduardo presenta las láminas 6 y 7 y me devuelve la palabra. Mientras tanto: app al frente, en F1.)*

---

## Demostración en vivo — 4 minutos

**Regla de oro:** hablar mientras escribo. Si me quedo en silencio tecleando, el tiempo se siente
el doble. Y decir en voz alta **el número** que aparece en pantalla.

### Entrada (10 s)

> «Les voy a mostrar el sistema funcionando, con una base de prueba y datos ficticios. Vamos a seguir
> un producto desde que **llega** al local hasta que aparece en un **reporte**.»

### 1 · Llega mercadería — F5 Compras (45 s)

| Hago | Escribo |
|---|---|
| **F5 Compras** → pestaña **Registrar factura** | |
| Proveedor | `Frutos del Sur` |
| Número de documento · Monto neto · Impuestos | `45678` · `42500` · `8075` |
| Código · Cantidad · Costo unitario neto | `ALM-GR` · `5` · `8500` |
| Código de lote | `L2024-001` |
| Botón **▾** de «Vence» → **›** → día **7** | debe quedar `2026-12-07` |
| **Agregar línea** → **Confirmar factura** | «Factura 45678 confirmada» |

> *(mientras escribo)* «Llega una factura del proveedor: 5 kilos de almendras a $8.500 el kilo. Como es
> un producto perecible, el sistema **exige** la fecha de vencimiento y el lote.»
>
> *(al agregar la línea)* «Fíjense aquí: el costo anterior era **$7.900**.»
>
> *(al confirmar)* «Con un clic pasaron tres cosas: entraron 5 kilos al stock, se creó el lote y el
> costo se actualizó a **$8.500**. En el sistema antiguo, esto no existía.»

### 2 · El sistema cuida lo que vence — F3 Inventario (20 s)

| Hago | Se ve |
|---|---|
| **F3 Inventario** → pestaña **Alertas** | Almendras · vence 07-12 · 5 kg · 10 % · **$13.491** |

> «El lote que acabo de ingresar ya aparece en **alertas**: vence en menos de un mes y el sistema
> sugiere venderlo con **10 % de descuento**, a $13.491. Es una sugerencia: la decisión es de la dueña.
> En una tienda de productos naturales, esto evita botar mercadería. El sistema antiguo no tenía ni
> un campo de vencimiento.»

*Solo si sobra tiempo:* botón **Ajustes y mermas** → `ALM-GR` · `0,1` · motivo `Rotura` →
**Registrar merma** («si se rompe una bolsa, se da de baja con motivo obligatorio»). Si se hace, el
stock queda en 4,9 kg y la auditoría muestra un registro más.

### 3 · Una venta en efectivo — F1 Operación (55 s)

| Hago | Escribo |
|---|---|
| **F1 Operación** → pestaña **Venta** → Código del producto | `ALM-GR` + Enter |
| Peso (kg) | `0,350` + Enter → **$5.247** |
| Clic en la línea → **Descuento a la línea** | `15` · `Cliente frecuente` → **Aplicar descuento** |
| **F12 Cobrar** → casilla de $20.000 | `1` |
| **Agregar pago** → **Cobrar solo registrando la venta** | **OK** |

> *(al entrar a F1, señalando la barra de abajo)* «La jornada de caja ya está abierta: la cajera la
> abre **contando los billetes**, aquí $50.000 de fondo. Así el cierre cuadra, que era uno de los
> problemas del sistema antiguo.»
>
> *(al pesar)* «Vendo almendras a granel: el sistema pide el **peso** y calcula solo: 350 gramos,
> **$5.247**.»
>
> *(al descontar)* «Le hago 15 % de descuento. El motivo es **obligatorio**, y queda en auditoría.
> Total: **$4.460**.»
>
> *(al cobrar)* «Paga con un billete de $20.000 y el sistema le dice a la cajera el vuelto:
> **$15.540**.»

### 4 · Una venta a crédito y la cuenta del cliente — F1 y F4 (60 s)

| Hago | Escribo |
|---|---|
| **Cliente de la venta** | `Juan Pérez` |
| Código del producto | `MIX-250` + Enter |
| Clic en la línea → botón **+** | cantidad **2** → **$7.980** |
| **F12 Cobrar** → **Crédito cliente** | se ve «cupo disponible $20.000» |
| **Agregar pago** → **Cobrar solo registrando la venta** | **OK** |
| **F4 Clientes** → clic en Juan → **Registrar abono** | `5000` → **Registrar abono** |
| Pestaña **Estado de cuenta** → Cliente | `Juan Pérez` |

> *(al cobrar)* «Esta venta va a la **cuenta de un cliente**. El sistema muestra su cupo disponible y, si
> la venta lo supera, **no la deja pasar**. Son $7.980.»
>
> *(en F4)* «En Clientes ya aparece su deuda. Registro un **abono** de $5.000.»
>
> *(en el estado de cuenta)* «Y este es su estado de cuenta del mes: el sistema aplica solo el **20 % de
> descuento** del crédito familiar. Total a pagar **$6.384**, saldo final **$2.980**. Antes, esto se
> llevaba en un cuaderno.»

### 5 · Todo queda registrado — F6 y F7 (30 s)

| Hago | Se ve |
|---|---|
| **F6 Reportes** | 2 ventas · **$12.440** |
| Pestaña **Rentabilidad** | ganancia $3.079 · margen **29,5 %** |
| **F7 Administración** → **Auditoría** | descuento, factura y proveedor |

> «Las dos ventas ya están en el reporte: **$12.440**. Y aquí está lo que más le importaba a las dueñas:
> la **rentabilidad real**, 29,5 % de margen, calculada con el costo que tenía el producto cuando se
> vendió.
>
> Por último, la **auditoría**: cada descuento y cada factura, con quién lo hizo y el valor
> de antes y de después. No se puede editar ni borrar.»

### Cierre (10 s)

> «Eso fue el sistema de punta a punta: compra, inventario, venta, crédito y reportes. Y todo lo que
> vieron funcionó **sin conexión a internet**. Le devuelvo la palabra a Victoria.»

---

## Si algo sale mal

| Problema | Qué hago | Qué digo |
|---|---|---|
| Un botón o un día del calendario no responde | Clic de nuevo | *(nada, sigo hablando)* |
| Aviso «falta la fecha de vencimiento» | OK → elegir el día otra vez → Agregar línea | «El sistema no deja ingresar un perecible sin su vencimiento» |
| Un cuadro se ve negro | Un clic dentro | *(nada)* |
| Abajo dice «Sin turno abierto» | Caja y corte → Abrir jornada → $20.000: `2` · $10.000: `1` → Confirmar | «Abro la jornada contando el fondo: $50.000» |
| El Mix queda en 1 | Clic en la línea → **+** | «Subo la cantidad a dos» |
| Me equivoco en un número | Seguir con el número que salió | «Los montos cambian, pero el flujo es el mismo» |
| Voy atrasado (más de 2:15 al terminar el paso 3) | Saltar el abono: ir directo a F6 | «El abono y el estado de cuenta están en el video» |
| La app se cierra | Lámina 9 (capturas) o el video | «Les muestro el mismo recorrido grabado» |

## Preguntas probables y respuestas cortas

| Pregunta | Respuesta |
|---|---|
| ¿Por qué no usaron Docker? | El PC del local tiene Windows 8.1 y Docker no corre ahí. Entregamos un ejecutable con PyInstaller, autorizado por la docente. |
| ¿Por qué Tkinter y no una web? | Tiene que funcionar sin internet y en un equipo antiguo. Tkinter viene con Python y no necesita navegador ni servidor. |
| ¿Qué pasa si se corta internet? | Se vende igual. Las operaciones quedan en una cola local y se envían solas al volver la conexión, sin duplicarse. |
| ¿Y si se corta la luz a mitad de una venta? | La venta se guarda en una sola transacción: o queda completa o no queda. |
| ¿Cómo aseguran la calidad? | 459 pruebas automáticas, 7 de ellas con la aplicación real de punta a punta, más el QA manual de Victoria: 94 hallazgos, ninguno abierto. |
| ¿Qué falta? | Migrar los datos del sistema antiguo y probar la impresora y el cajón reales en el local. |
| ¿Qué es el texto naranja del descuento? | Una nota interna: el descuento por línea está pendiente de validación final con la dueña. |
| ¿Quién puede anular una venta? | Solo la administradora, con motivo, y solo en la jornada abierta. La venta no se borra: queda marcada. |
