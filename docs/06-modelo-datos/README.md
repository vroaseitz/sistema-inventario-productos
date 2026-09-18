# 06 · Modelo de datos

Modelo entidad-relación y diccionario de datos del sistema nuevo, construido a partir
de los hallazgos de `informe_analisis_bd_naturalsur.pdf` (análisis de
`PDVDATA.FDB`, Firebird 2.0.3, corte al 24-07-2026) y de las 44 historias de usuario
del Product Backlog.

## 0. Las nueve correcciones respecto al sistema legado

Cada entidad y restricción de este modelo responde a un hallazgo concreto del
análisis de la base legada, no a una preferencia de diseño:

| # | Corrección | Hallazgo que la justifica |
| --- | --- | --- |
| 1 | Montos en `NUMERIC`, nunca en punto flotante | Cabecera y detalle de ventas difieren en montos sin causa contable |
| 2 | Costo desglosado en `neto`, `IVA` e `impuesto adicional` | El costo consolidado impedía recuperar el IVA crédito y distorsionaba el margen (implementado: `Costo` en `src/pos/dominio/value_objects.py`) |
| 3 | Identificador interno independiente del código de barras | 20,4 % de códigos improvisados, 48 descripciones duplicadas |
| 4 | Categoría obligatoria, separada de atributos dietarios | 69,7 % de la venta caía en «Sin Departamento»; el campo mezclaba formato físico, dieta y familia en un solo valor |
| 5 | Vencimiento y lote en tabla propia | No existía ningún campo de vencimiento en las 241 columnas del esquema legado |
| 6 | Motivo obligatorio en ajustes de inventario | 29.715 ajustes manuales sin causa registrada |
| 7 | Auditoría de quién hizo cada cambio | La tabla equivalente del sistema legado estaba vacía |
| 8 | Autenticación local, con auditoría, sin roles diferenciados (perfil único) | Credencial genérica compartida por todo el local. Decisión de alcance del 16-09-2026: se prioriza login + auditoría (2 de 3 sub-objetivos de OE12); el control de acceso por roles queda como incremento posterior, aún sin tarea ni fecha |
| 9 | Medios de pago como tabla hija de la venta | La transferencia se registraba como efectivo; el pago mixto era imposible |

Además, tres decisiones que los datos exigieron aunque no estaban en la lista
original:

- **La ganancia es una columna generada, no un campo que se escribe** — el defecto
  central del sistema legado (guardar el margen de la unidad completa en vez del
  vendido, hasta 148,3 % de ganancia declarada en productos a granel) es imposible
  de reproducir si la ganancia se deriva en vez de guardarse.
- **La línea de venta guarda una instantánea del costo** — hoy no existe costo
  histórico: calcular el margen de una venta pasada usa el costo de hoy.
- **`costo_cargado` es un booleano separado del monto** — 358 productos con costo
  cero generaban 100 % de margen falso porque el sistema no distinguía «cuesta
  cero» de «no sé cuánto cuesta» (implementado: `Producto.costo: Costo | None`).
- **`medio_pago` es `tarjeta`, no `debito`/`credito` separados** — el terminal TUU
  solo pide seleccionar «tarjeta» al cobrar; no distingue débito de crédito ni se
  lo muestra a quien atiende, así que pedirle esa distinción al sistema sería
  forzarla a adivinar. El desglose real (débito/crédito) lo entrega el propio
  cierre del terminal, y la conciliación de caja compara el total de `tarjeta` del
  sistema contra esa suma — no reconstruye el desglose. Corrige HU-VTA-03,
  HU-CAJ-02 y HU-CAJ-03.

## 1. Diagrama entidad-relación

```mermaid
erDiagram
    CATEGORIA ||--o{ PRODUCTO : clasifica
    PRODUCTO ||--o{ CODIGO_BARRA : tiene
    PRODUCTO }o--o{ ATRIBUTO_DIETARIO : etiqueta
    PRODUCTO_ATRIBUTO_DIETARIO }o--|| PRODUCTO : ""
    PRODUCTO_ATRIBUTO_DIETARIO }o--|| ATRIBUTO_DIETARIO : ""
    PRODUCTO ||--o{ LOTE : tiene
    PRODUCTO ||--o| EXISTENCIA : tiene
    PRODUCTO ||--o{ MOVIMIENTO_INVENTARIO : afecta
    MOTIVO_MOVIMIENTO ||--o{ MOVIMIENTO_INVENTARIO : justifica
    PRODUCTO ||--o{ VENTA_DETALLE : vende
    VENTA ||--|{ VENTA_DETALLE : contiene
    VENTA ||--|{ VENTA_PAGO : cobra
    VENTA }o--o| CLIENTE : "a nombre de"
    VENTA }o--|| TURNO_CAJA : "dentro de"
    VENTA }o--|| USUARIO : registra
    CLIENTE ||--o{ MOVIMIENTO_CREDITO : acumula
    VENTA ||--o| MOVIMIENTO_CREDITO : origina
    USUARIO ||--o{ TURNO_CAJA : abre
    USUARIO ||--o{ AUDITORIA : genera
    USUARIO ||--o{ MOVIMIENTO_INVENTARIO : ejecuta
    PROVEEDOR ||--o{ FACTURA_COMPRA : emite
    FACTURA_COMPRA ||--|{ FACTURA_COMPRA_DETALLE : detalla
    PRODUCTO ||--o{ FACTURA_COMPRA_DETALLE : compra
    FACTURA_COMPRA_DETALLE ||--o| LOTE : genera

    CATEGORIA {
        int id PK
        text nombre UK
    }
    ATRIBUTO_DIETARIO {
        int id PK
        text nombre UK
    }
    PRODUCTO {
        int id PK
        text nombre
        int categoria_id FK
        text unidad_venta "UNIDAD | GRANEL"
        numeric precio_venta "CHECK > 0"
        numeric costo_neto
        numeric costo_iva
        numeric costo_impuesto_adicional
        numeric costo_total "GENERATED neto+iva+imp_adicional"
        bool costo_cargado
        bool es_perecible
        int dias_aviso_vencimiento
        bool activo
        int creado_por FK
        timestamp creado_en
    }
    CODIGO_BARRA {
        int id PK
        int producto_id FK
        text codigo UK
    }
    LOTE {
        int id PK
        int producto_id FK
        date fecha_vencimiento
        numeric saldo "CHECK >= 0"
    }
    EXISTENCIA {
        int producto_id PK_FK
        numeric cantidad "CHECK >= 0"
    }
    MOTIVO_MOVIMIENTO {
        int id PK
        text nombre
        bool requiere_comentario
    }
    MOVIMIENTO_INVENTARIO {
        int id PK
        int producto_id FK
        text tipo "entrada|salida|ajuste|devolucion"
        numeric cantidad
        int motivo_id FK "NOT NULL"
        text comentario
        int usuario_id FK
        timestamp creado_en
    }
    CLIENTE {
        int id PK
        text nombre
        text rut
        bool tiene_credito
    }
    MOVIMIENTO_CREDITO {
        int id PK
        int cliente_id FK
        int venta_id FK "NULL si es abono suelto"
        text tipo "cargo|abono"
        numeric monto
        timestamp creado_en
    }
    USUARIO {
        int id PK
        text nombre
        text correo UK
        text contrasena_hash
        bool activo
    }
    TURNO_CAJA {
        int id PK
        int usuario_id FK
        numeric fondo_inicial
        timestamp abierto_en
        timestamp cerrado_en "NULL = turno abierto; UNIQUE INDEX WHERE cerrado_en IS NULL"
    }
    VENTA {
        int id PK
        int turno_caja_id FK
        int cliente_id FK
        int usuario_id FK
        text estado "pagada|anulada"
        text motivo_anulacion "NOT NULL si estado = anulada"
        timestamp creado_en
    }
    VENTA_DETALLE {
        int id PK
        int venta_id FK
        int producto_id FK
        numeric cantidad "CHECK > 0"
        numeric precio_unitario
        numeric costo_unitario "instantanea del costo neto"
        numeric descuento_linea
        numeric ganancia "GENERATED cantidad*(precio-costo)-descuento"
    }
    VENTA_PAGO {
        int id PK
        int venta_id FK
        text medio_pago "efectivo|tarjeta|transferencia|credito_cliente"
        numeric monto
    }
    AUDITORIA {
        int id PK
        text tabla
        text registro_id
        int usuario_id FK
        text accion
        jsonb datos_antes
        jsonb datos_despues
        timestamp creado_en
    }
    PROVEEDOR {
        int id PK
        text nombre
        text rut
    }
    FACTURA_COMPRA {
        int id PK
        int proveedor_id FK
        text numero_factura
        date fecha
        numeric monto_neto
        int usuario_id FK
    }
    FACTURA_COMPRA_DETALLE {
        int id PK
        int factura_id FK
        int producto_id FK
        numeric cantidad
        numeric costo_unitario_neto
        int lote_id FK "NULL si el producto no es perecible"
    }
```

## 2. Restricciones que hacen imposibles los errores encontrados

| Restricción | Error que previene |
| --- | --- |
| `CHECK (precio_venta > 0)` | Productos con precio cero |
| `CHECK (NOT costo_cargado OR precio_venta >= costo_total)` | Vender bajo costo por error de dato (9 casos detectados; las liquidaciones reales quedan fuera de este check y se manejan como excepción explícita, ver HU-INV-06) |
| `CHECK (cantidad > 0)` en `venta_detalle` | Líneas de importe negativo |
| `CHECK (estado <> 'anulada' OR motivo_anulacion IS NOT NULL)` | Anulaciones sin motivo ni autor (2.781 casos en el sistema legado) |
| `UNIQUE INDEX ... WHERE cerrado_en IS NULL` en `turno_caja` | Dos turnos de caja abiertos a la vez |
| `motivo_id NOT NULL` en `movimiento_inventario` | Ajustes de inventario sin causa (29.715 casos) |
| `categoria_id NOT NULL` en `producto` | Productos sin categoría (3.300 de 4.109 en el catálogo legado) |

La cantidad anómala en ventas a granel (ej. 705 kg de salmón en vez de 0,705 kg,
que distorsionó un tercio de la venta de un período) **no se resuelve con un CHECK
fijo** porque el rango razonable depende del producto. Queda como requisito
funcional: confirmar con la usuaria cuando la cantidad supere un múltiplo del
promedio histórico de ese producto — no como restricción de base de datos.

## 3. Alcance de la migración

El catálogo legado tiene 4.109 productos, pero solo 1.135 se vendieron desde el
2026-03-02 (cubren el 100 % de la venta del período analizado). Se migran esos
1.135, marcando como `activo = false` los que no rotan hace más de 90 días. La
migración completa de los 4.109 es inviable: 3.300 no tienen categoría y 358 no
tienen costo.

## 4. Por qué `categoria` y `atributo_dietario` son tablas separadas

El sistema legado tenía dos catálogos de "departamento" (uno de ellos huérfano) que
mezclaban tres criterios distintos en un solo campo: formato físico (LIQUIDO,
CONGELADO), restricción dietaria (VEGANO, SIN GLUTEN, KETO) y familia de producto
(CAFE/TE, FRUTAS VERDURAS). Un producto puede ser vegano, sin gluten **y** de la
familia "frutos secos" a la vez — el modelo legado solo admitía uno de los tres.
Por eso el modelo nuevo separa `categoria` (una por producto, obligatoria) de
`atributo_dietario` (muchos por producto, vía `producto_atributo_dietario`).

## 5. Mapeo con el sistema legado

DDL equivalente para PostgreSQL/Supabase: `database/migraciones/`. Diccionario de
tablas legadas y su destino en este modelo: ver `docs/09-plan-migracion/`.

> **Responde al instructivo:** modelo de datos, ER clásico para SQL (obligatorio transversal).
