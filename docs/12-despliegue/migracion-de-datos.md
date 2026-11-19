# Migración de datos desde el sistema antiguo

Carga los productos y clientes que QA extrajo del respaldo del 17-11-2026 (QA 18-11).
Comando: `scripts/importar_migracion.py`. Caso de uso: `aplicacion/casos_uso/migrar_datos_legados.py`.

## Archivos de entrada

CSV con separador `;` y UTF-8 con BOM. **No van al repositorio** y los de clientes (datos personales)
se **borran** al terminar la migración.

| Archivo | Columnas que usa el importador |
|---|---|
| `productos_a_migrar.csv` | codigo, nombre, unidad_venta, categoria, precio_venta_con_iva, costo_neto, iva, impuesto_adicional, existencia, stock_minimo |
| `clientes_a_migrar_PRIVADO.csv` | nombre, telefono, observaciones, cupo, deuda_actual, ultimo_pago |

## Cómo ejecutarlo

Desde la raíz del repo, con la base que usa la aplicación (`POS_SQLITE_PATH`):

```bash
# 1. Ensayo: corre todo sobre una copia en memoria; la base real no se modifica
PYTHONPATH=src python scripts/importar_migracion.py \
  --productos productos_a_migrar.csv --clientes clientes_a_migrar_PRIVADO.csv --simulacro

# 2. Carga real (cierra la aplicación antes)
PYTHONPATH=src python scripts/importar_migracion.py \
  --productos productos_a_migrar.csv --clientes clientes_a_migrar_PRIVADO.csv
```

Opciones: `--fecha-saldo AAAA-MM-DD` (por defecto, el último día del mes anterior), `--contacto-pendiente
"texto"`, `--sin-cola` (no encola para Supabase).

## Qué hace

- **Productos:** crea cada uno con su categoría (la crea si falta; «Sin categoría» incluida), precio,
  costo neto, stock mínimo y existencia. La existencia queda en el historial como movimiento
  **«Carga inicial»** (solo si es mayor que 0). Todo se encola para Supabase.
- **Clientes:** crea cada uno con su cupo. La deuda actual queda como un consumo **«Saldo anterior»**
  (con el último pago en el detalle), fechado antes del ciclo en curso para que no cuente como consumo
  del mes ni reciba el 20 % del crédito familiar de este mes.
- **Idempotente:** un código o un nombre de cliente que ya existe se omite; no se pisa el stock ni se
  duplica el saldo. Se puede correr dos veces.
- **Resumen:** leídos, cargados, omitidos y rechazados con su motivo (sin nombres de clientes: se
  identifican por número de fila).

## Decisiones y límites (para revisar con QA)

1. **Productos sin nombre (5 en el archivo):** si el código es un texto (4 casos, p. ej. «FUDGE»), se usa
   el código como nombre y se avisa; si es solo un número (1 caso) se rechaza.
2. **Clientes sin teléfono ni correo (15 de 16):** el sistema exige un contacto, así que quedan con
   «Sin teléfono (migración)»; hay que completarlo desde F4. El cliente sin nombre (1) se rechaza.
3. **IVA e impuesto adicional (IABA):** la PO definió el 18-11 que el IABA se suma al costo de la bebida
   y que en la migración no hay que corregir nada: el `costo_neto` de los ~138 líquidos (costo antiguo
   ÷ 1,19) ya lo incluye de forma aproximada. El importador no separa el IABA (lo avisa en el
   resumen); si se quiere afinar, se marca la tasa del producto en F2 y se corrige su costo neto.
4. **Duplicados y revisión de Roxana:** se migran todos; desactivar los que Roxana indique, desde F2.

## Pruebas

`tests/unitarias/test_migrar_datos_legados.py` (CSV de ejemplo, sin datos reales): categoría, costo,
carga inicial, saldo anterior, idempotencia, cola de sincronización, filas inválidas, simulacro.

## Antes de implantar (hallazgos del ensayo con los datos reales, 18-11)

- **Supabase debe aceptar precio 0:** 25 productos traen precio $0 y la nube exige `precio_venta > 0`;
  la cola se detiene en el primer rechazo. Aplicar `database/migraciones/010_permitir_precio_cero.sql`
  (y la 009) y verificar con `scripts/verificar_supabase.py` antes de la primera sincronización.
- **Volumen:** la migración deja unas 3.400 operaciones pendientes. Se envían una por una (una
  conexión por operación): hacer la primera carga con el botón «Sincronizar» y buena conexión, antes
  de abrir. El cierre de jornada solo envía durante 45 s y deja el resto para el siguiente.
- **Datos al día:** el importador omite lo que ya existe, así que NO actualiza stock ni deudas al
  re-ejecutarlo. Importar siempre en una base vacía, con la extracción hecha en el cierre del último
  día del sistema antiguo.
- **Dónde corre:** es un script de Python (no va dentro del .exe). Importar en la VM y copiar la base
  al local junto con el .exe, o empaquetarlo aparte. Borrar los CSV de clientes al terminar.
