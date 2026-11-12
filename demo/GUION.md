# Guion de la presentación del 13-11 — Fernando

Láminas 4 y 5 + demostración en vivo (4 min). Presentación online, después del primer grupo.

## Antes de entrar a la reunión (5 min)

1. Doble clic en `demo/reiniciar_demo.command` → deja la base como nueva
   (proveedor «Frutos del Sur» y cliente «Juan Pérez» ya creados).
2. Doble clic en `demo/abrir_demo.command` → abre la app.
3. Si el cuadro de ingreso se ve negro, hacer un clic dentro. Entrar con `admin`
   (la clave está en el encabezado de `scripts/sembrar_demo_e2e.py`).
4. Dejar la app en **F1 Operación**, con la ventana a la vista y sin otras ventanas encima.
5. Cerrar WhatsApp y notificaciones. Tener abierto el PPT en la lámina 9 (capturas) por si falla algo.
6. Al compartir pantalla: compartir **la pantalla completa**, no solo la ventana (los diálogos son
   ventanas aparte y no se verían).

---

## Lámina 4 · Stack tecnológico (45 s)

> «El stack lo definió una restricción: el computador del local tiene Windows 8.1.
> Python 3.11 es la última versión que lo soporta. Docker no corre ahí, así que empaquetamos con
> PyInstaller, con autorización de la docente. La interfaz es Tkinter, que viene con Python.
> SQLite es la base de trabajo en el local y Supabase es la copia en la nube.
> Para la calidad usamos pytest, ruff y GitHub Actions.»

## Lámina 5 · Arquitectura e integración (1 min)

> «La arquitectura es por capas: interfaz, casos de uso y dominio. El dominio tiene las reglas del
> negocio y no depende ni de la pantalla ni de la base de datos.
> La aplicación trabaja sobre SQLite local, así que si se cae internet se sigue vendiendo.
> Cada operación entra a una cola con un identificador único y, cuando vuelve la conexión, se publica
> en Supabase. Si un envío se corta y se reintenta, no se duplica.
> La migración desde el sistema antiguo es un proceso aparte que todavía no implementamos.
> Le paso a Eduardo.»

*(Eduardo: láminas 6 y 7. Después vuelve a ti para la demo.)*

---

## Demostración en vivo (4 min)

**Frase de entrada:** «Les muestro el sistema funcionando, con una base de prueba y datos ficticios.»

### Paso 1 · F5 Compras (45 s)

| # | Qué hago | Qué escribo |
|---|---|---|
| 1 | Clic en **F5 Compras** → pestaña **Registrar factura** | |
| 2 | Proveedor | elegir `Frutos del Sur` |
| 3 | Número de documento | `45678` |
| 4 | Monto neto | `42500` |
| 5 | Impuestos | `8075` → Total **$50.575** |
| 6 | Código de producto | `ALM-GR` |
| 7 | Cantidad | `5` |
| 8 | Costo unitario neto | `8500` |
| 9 | Código de lote | `L2024-001` |
| 10 | Botón **▾** de «Vence» → flecha **›** (diciembre) → día **7** | comprobar que quedó `2026-12-07` |
| 11 | **Agregar línea** | Diferencia con el neto **$0** · costo anterior **$7.900** |
| 12 | **Confirmar factura** | mensaje «Factura 45678 confirmada» |

> «Registro la factura de un proveedor. Al confirmarla entran 5 kilos al stock, se crea el lote con su
> fecha de vencimiento y el costo de las almendras sube de $7.900 a $8.500.»

### Paso 2 · F3 Inventario (35 s)

| # | Qué hago | Qué escribo |
|---|---|---|
| 1 | Clic en **F3 Inventario** → pestaña **Alertas** | se ve: 24 días · 10 % · precio sugerido **$13.491** |
| 2 | Botón **Ajustes y mermas** | |
| 3 | Código de producto | `ALM-GR` |
| 4 | Cantidad a dar de baja | `0,1` |
| 5 | Motivo | `Rotura` → abajo dice «Resultante: 4.9» |
| 6 | **Registrar merma** | la alerta pasa a **4,9 kg** |

> «El sistema avisa que este lote vence pronto y sugiere un 10 % de descuento. Es una sugerencia: no
> cambia el precio solo. Registro una merma de 100 gramos, con motivo obligatorio, y el stock baja a
> 4,9 kilos.»

### Paso 3 · F1 Venta en efectivo (70 s)

| # | Qué hago | Qué escribo |
|---|---|---|
| 1 | **F1 Operación** → pestaña **Caja y corte** → **Abrir jornada** | $20.000: `2` · $10.000: `1` → Total **$50.000** → **Confirmar** |
| 2 | Pestaña **Venta** → Código del producto | `ALM-GR` + Enter |
| 3 | Peso (kg) | `0,350` + Enter → importe **$5.247** |
| 4 | Clic en la línea → **Descuento a la línea** | Valor `15` · Motivo `Cliente frecuente` → importe final **$4.460** → **Aplicar descuento** |
| 5 | **F12 Cobrar** → en $20.000 | `1` → «Pagó con $20.000 · su cambio **$15.540**» |
| 6 | **Agregar pago** → **Cobrar solo registrando la venta** | «Venta #1 registrada. Cambio a entregar: $15.540» → **OK** |

> «Abro la jornada contando el fondo: $50.000. Vendo almendras a granel: el sistema pide el peso y
> calcula $5.247. Aplico 15 % de descuento con su motivo y queda en $4.460. La clienta paga con
> $20.000 y el sistema indica el vuelto: $15.540.»

### Paso 4 · Venta a crédito y cuenta del cliente (60 s)

| # | Qué hago | Qué escribo |
|---|---|---|
| 1 | **Cliente de la venta** | elegir `Juan Pérez` |
| 2 | Código del producto | `MIX-250` + Enter |
| 3 | Clic en la línea → botón **+** | cantidad **2** → **$7.980** |
| 4 | **F12 Cobrar** → **Crédito cliente** | se ve «cupo disponible $20.000» |
| 5 | **Agregar pago** → **Cobrar solo registrando la venta** | «Venta #2 registrada» → **OK** |
| 6 | **F4 Clientes** | Juan: deuda **$7.980** · disponible **$12.020** |
| 7 | Clic en Juan → **Registrar abono** | Monto `5000` → saldo resultante **$2.980** → **Registrar abono** |
| 8 | Pestaña **Estado de cuenta** → Cliente | elegir `Juan Pérez` |

> «La segunda venta va a la cuenta de un cliente con crédito: $7.980, y el sistema controla su cupo.
> Después registro un abono de $5.000. El estado de cuenta del mes aplica el 20 % de descuento del
> crédito familiar: total a pagar $6.384 y saldo final $2.980.»

### Paso 5 · F6 Reportes y F7 Auditoría (30 s)

| # | Qué hago | Qué se ve |
|---|---|---|
| 1 | **F6 Reportes** (pestaña Ventas) | 2 ventas · total **$12.440** · ticket promedio $6.220 |
| 2 | Pestaña **Rentabilidad** | ganancia **$3.079** sobre $10.454 netos · margen **29,5 %** |
| 3 | **F7 Administración** → pestaña **Auditoría** | descuento, merma, factura y proveedor, con antes y después |

> «En reportes quedan las dos ventas, $12.440, y la rentabilidad real: 29,5 % de margen, calculada
> con el costo que tenía el producto al venderse. Y en auditoría queda cada cambio sensible, con quién
> lo hizo y el valor de antes y de después. Es de solo lectura.»

**Cierre:** «Eso es el sistema de punta a punta, y todo funcionó sin internet. Le devuelvo la palabra a Victoria.»

---

## Si algo sale mal

| Problema | Qué hacer |
|---|---|
| Un botón o un día del calendario no responde | Hacer clic de nuevo (el primer clic a veces solo activa la ventana) |
| Aviso «falta la fecha de vencimiento» | OK → elegir el día en el calendario otra vez → Agregar línea |
| Un diálogo se ve negro | Un clic dentro de él |
| El Mix queda en 1 | Seleccionar la línea y apretar **+** |
| Se acaba el tiempo | Saltar el paso 2 (mermas) y decir: «la alerta y la merma están en el video» |
| La app se cierra | Mostrar la lámina 9 (capturas) o el video de 4 minutos |
| Preguntan por el texto naranja del descuento | «Es una nota interna: el descuento por línea está pendiente de validación final con la dueña» |

## Preguntas probables

- **¿Por qué no Docker?** El PC del local tiene Windows 8.1 y Docker no corre ahí; por eso un
  ejecutable con PyInstaller (ADR 0003, autorizado por la docente).
- **¿Qué pasa sin internet?** Se vende igual sobre SQLite; la cola guarda los pendientes y los publica
  al volver la conexión, sin duplicar.
- **¿Qué falta?** La migración de datos desde el sistema antiguo y probar la impresora real.
- **¿Cómo se prueba?** 459 pruebas automáticas, 7 de ellas con la aplicación real de punta a punta, más
  el QA manual de Victoria (94 hallazgos registrados, ninguno abierto).
