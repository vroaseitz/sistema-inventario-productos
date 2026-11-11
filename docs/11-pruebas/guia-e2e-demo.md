# Guía E2E rápida — Emporio NaturalSur

**Video demo (7 escenas).** Esta guía se ejecutó completa con la app real en macOS, sobre una base nueva, y de esa corrida salió el video (`docs/video/e2e-hyperframes/`). Todos los valores de las tablas son los que se vieron en pantalla y se comprobaron en la base.

- **Duración del video editado:** 4 min 9 s sin voz. Sin pausas, con cursor resaltado, recuadros verdes en lo importante y subtítulos que dicen qué se hace.
- **Duración sugerida si se narra en vivo:** 10–12 min (columna «Con narración»).
- **Módulos que cubre:** F1 Operación, F3 Inventario, F4 Clientes, F5 Compras, F6 Reportes y F7 Administración.

## Preparación (antes de grabar)

1. Crear la base de prueba. El script se niega a sobrescribir una base existente:

   ```bash
   PYTHONPATH=src python scripts/sembrar_demo_e2e.py /ruta/demo.db
   ```

2. Abrir la app apuntando a esa base y **sin Supabase**:

   ```bash
   PYTHONPATH=src POS_SQLITE_PATH=/ruta/demo.db SUPABASE_DB_URL= python -m pos.interfaz.ventana_principal
   ```

3. Entrar con la administradora de prueba: usuario `admin`, contraseña `admin-demo-2026`.

### Datos de la prueba

| Dato | Valor |
|---|---|
| Vendedora (se crea en la escena 1) | `maria.gonzalez` / `venta2024` |
| Proveedor | Frutos del Sur |
| Factura | N° 45678 · neto $42.500 · IVA $8.075 · total $50.575 |
| Producto granel | Almendras a granel (`ALM-GR`) · $14.990/kg · costo $7.900 · perecible, aviso a 45 días |
| Producto por unidad | Mix de frutos secos 250 g (`MIX-250`) · $3.990 · costo $2.200 · stock 20 |
| Lote | `L2024-001` · vence 2026-12-07 (30 días desde el 07-11) |
| Cliente | Juan Pérez · +56 9 1234 5678 |
| Fondo de caja | $50.000 (2 billetes de $20.000 y 1 de $10.000) |

### Lista antes de grabar

- [ ] Base nueva sembrada con el script (sin ventas, sin proveedores, sin clientes).
- [ ] La app abre con `SUPABASE_DB_URL` vacío; abajo debe decir «sin Supabase configurado» al sincronizar.
- [ ] Ventana de la app a 1:1, sin otras ventanas encima; reloj del sistema en la fecha de la grabación.
- [ ] Tamaño de pantalla fijo: los diálogos de Tk salen en lugares distintos en cada ingreso.
- [ ] Si un diálogo se ve negro, hacer un clic dentro de él (Tk en macOS lo dibuja al primer clic).
- [ ] Grabación en marcha: `screencapture -v -C -V <segundos> demo.mov` (se detiene sola al cumplir el tiempo).

## Escena 1 · Ingreso y vendedora (F7) — 1:30

| Acción | Datos |
|---|---|
| Entrar como administradora | `admin` / `admin-demo-2026` |
| F7 Administración → Usuarios → Nuevo usuario | Usuario `maria.gonzalez` · contraseña `venta2024` · perfil **Vendedora** → Crear usuario |
| Cerrar sesión y entrar como María | `maria.gonzalez` / `venta2024` |
| Comprobar el acceso | Solo F1 Operación activa; F2 a F7 quedan en gris |
| Cerrar sesión y volver a la administradora | `admin` |

**Narración:** «La administradora crea a María como Vendedora. Al entrar con su cuenta, María solo ve Operación: el resto de los módulos queda bloqueado.»

## Escena 2 · Proveedor y factura de compra (F5) — 2:00

| Acción | Datos |
|---|---|
| F5 Compras → Nuevo proveedor | Nombre `Frutos del Sur` · contacto (correo o teléfono) → Crear proveedor |
| Pestaña Registrar factura | Proveedor `Frutos del Sur` · N° de documento `45678` |
| Importes de la factura | Monto neto `42500` · Impuestos (IVA 19 %) `8075` → Total $50.575 |
| Detalle del producto | Código `ALM-GR` · cantidad `5` (kg) · costo unitario neto `8500` |
| Vencimiento y lote | Vence `2026-12-07`, elegido en el calendario · código de lote `L2024-001` |
| Agregar línea | Suma del detalle $42.500 · diferencia con el neto $0 · «Costo anterior» $7.900 |
| Confirmar factura (Ctrl+Enter) | Mensaje «Factura 45678 confirmada: costo actualizado y stock ingresado» |

**Narración:** «Se da de alta al proveedor y se registra la factura. Al confirmarla, el costo de las almendras sube de $7.900 a $8.500 y entran 5 kg al lote L2024-001.»

**Comprobación:** factura `45678` en estado confirmada; lote `L2024-001` con saldo 5; costo neto de `ALM-GR` en $8.500.

## Escena 3 · Stock, alerta de vencimiento y merma (F3) — 1:30

| Acción | Datos |
|---|---|
| F3 Inventario → Existencias | Almendras 5 kg · Mix 20 |
| Lotes y vencimientos | `L2024-001` · vence 2026-12-07 · saldo 5 |
| Alertas | Vence en 30 días · saldo 5 · precio $14.990 · descuento sugerido 10 % · precio sugerido $13.491 |
| Ajustes y mermas | Código `ALM-GR` · cantidad `0,1` · motivo **Rotura** · observación «Bolsa rota al fraccionar» |
| Registrar merma | Existencia 5 → 4,9 (se ve antes de confirmar) |

**Narración:** «La alerta propone un 10 % de descuento sobre el lote que vence. Es una sugerencia y no cambia el precio. Después se registra una merma de 100 g y el stock baja a 4,9 kg.»

**Comprobación:** existencia de `ALM-GR` = 4,9 y saldo del lote = 4,9.

## Escena 4 · Cliente con crédito (F4) — 0:45

| Acción | Datos |
|---|---|
| F4 Clientes → Nuevo cliente | Nombre `Juan Pérez` · teléfono `+56 9 1234 5678` → Guardar cliente |

**Narración:** «Se crea al cliente. El crédito es solo para familiares, según lo definido por las propietarias.»

## Escena 5 · Jornada y venta completa (F1) — 3:00

| Acción | Datos |
|---|---|
| F1 → Caja y corte → Abrir jornada | Billetes: 2 × $20.000 + 1 × $10.000 → total $50.000 → Confirmar |
| **Venta 1** · Venta → código | `ALM-GR` |
| Diálogo de peso | `0,350` kg → importe $5.247 → Agregar |
| Descuento a la línea (F9) | Seleccionar la línea · tipo Porcentaje · valor `15` · motivo **Cliente frecuente** → descuento $787 · importe final $4.460 |
| Cobrar (F12) → Efectivo | 1 billete de $20.000 → «Pagó con $20.000 · su cambio $15.540» → Agregar pago |
| Cobrar solo registrando (F2) | «Venta #1 registrada con éxito. Cambio a entregar: $15.540» |
| **Venta 2** · Cliente de la venta | `Juan Pérez` |
| Producto | `MIX-250`, cantidad 2 → $7.980 |
| Cobrar (F12) → Crédito cliente | Cliente Juan Pérez · monto a cargar $7.980 → Agregar pago → F2 |

**Narración:** «Se abre la jornada con $50.000. En la primera venta, las almendras se pesan, llevan 15 % de descuento con su motivo y se pagan con $20.000. En la segunda, los dos Mix se cargan a la cuenta de Juan.»

**Comprobación:** descuento de línea 787 con motivo «Cliente frecuente»; pago en efectivo 4.460 con entrega de 20.000; pago a crédito 7.980; existencia de `MIX-250` = 18.

## Escena 6 · Cuenta y abono (F4) — 1:30

| Acción | Datos |
|---|---|
| F4 → seleccionar a Juan → Ver cuenta | Consumo de la venta N° 2: $7.980 · saldo $7.980 |
| Registrar abono | Monto `5000` · medio Transferencia → saldo resultante $2.980 |
| Pestaña Estado de cuenta (ciclo de noviembre) | Consumos $7.980 · descuento del crédito familiar (20 %) −$1.596 · **total a pagar $6.384** · abonos $5.000 · **saldo final $2.980** |

**Narración:** «El abono baja el saldo a $2.980. El estado mensual descuenta el 20 % de los consumos del ciclo y deja el total a pagar en $6.384.»

## Escena 7 · Reportes y auditoría (F6 y F7) — 1:30

| Acción | Datos |
|---|---|
| F6 Reportes → Ventas (hoy) | 2 ventas · total $12.440 · ticket promedio $6.220 · categoría «Frutos secos y semillas» $12.440 · crédito $7.980 y efectivo $4.460 |
| Pestaña Rentabilidad (desde el 01-11) | Mix: venta neta $6.706, costo $4.400, margen 34,4 % · Almendras: venta neta $3.748, costo $2.975, margen 20,6 % · **ganancia $3.079 sobre $10.454 netos (29,5 %)** |
| F7 Administración → Auditoría | 5 registros, de más nuevo a más antiguo: descuento a la línea, merma, confirmación de factura, nuevo proveedor y alta de usuario |

**Narración:** «Cada venta y cada cambio sensible queda en reportes y en la auditoría, con su antes y su después. La auditoría es de solo lectura.»

## Tiempos

| Escena | En el video | Con narración |
|---|---|---|
| 1 · Ingreso y vendedora | 0:44 | 1:30 |
| 2 · Proveedor y factura | 0:32 | 2:00 |
| 3 · Stock, alerta y merma | 0:26 | 1:30 |
| 4 · Cliente con crédito | 0:10 | 0:45 |
| 5 · Jornada y venta completa | 1:11 | 3:00 |
| 6 · Cuenta y abono | 0:25 | 1:30 |
| 7 · Reportes y auditoría | 0:28 | 1:30 |
| **Total** | **3:56** (más 13 s de intro y cierre) | **≈ 11:45** |

## Diferencias con la guía original

La guía original describía un sistema genérico. Lo que cambió al ejecutarla con la app real:

- **No hay RUT.** Ni el proveedor (solo nombre y contacto) ni el cliente (nombre, teléfono, correo y observaciones) lo piden.
- **Lote y vencimiento son obligatorios** en un producto perecible. El vencimiento se elige con el calendario; no se escribe.
- **Neto e IVA se digitan** en la factura y la suma del detalle debe cuadrar con el neto (diferencia $0).
- **El descuento sugerido** de la alerta (10 %) es una sugerencia; no modifica el precio.
- **El descuento a la línea** exige un motivo de una lista (Cortesía, Producto dañado, Cliente frecuente, Error de precio, Otro).
- **El crédito** se cobra con el medio «Crédito cliente» y solo existe para clientes creados en F4.
- **Para cambiar de usuario** hay que cerrar sesión; la vendedora no puede abrir F2 a F7.
- **Con productos por unidad,** escribir el código agrega 1 unidad al instante; la cantidad se sube con el botón «+».

## Si algo sale distinto

- El saldo del cliente no se guarda: se calcula sumando sus movimientos. Un error se corrige con otro movimiento, no editando.
- Para repetir la prueba hay que sembrar **otra** base; la anterior ya tiene ventas, factura y usuarios.
