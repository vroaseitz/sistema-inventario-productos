# 07 · Diagramas UML

Diagramas mínimos exigidos por el instructivo.

| Diagrama | Estado |
| --- | --- |
| Casos de uso | ✅ |
| Clases | ✅ |
| Secuencia de la funcionalidad principal | ✅ |
| Componentes | ✅ |

> **Responde al instructivo:** diagramas UML mínimos (obligatorio transversal).
>
> La funcionalidad principal para el diagrama de secuencia es el **registro de una venta**.

## 1. Casos de uso

**Perfil único** (HU-USR-01/03 del Product Backlog, decisión de alcance del
16-09-2026): se elimina la distinción Administradora/Vendedora. Cualquier
usuaria autenticada accede a todos los casos de uso; el control de acceso por
rol queda como incremento posterior, sin tarea ni fecha todavía. El
`prototipo-naturalsur-pantalla-completa.html` (`docs/08-diseno/`) sigue
mostrando el selector de perfil porque es anterior a esta decisión — no
representa el alcance actual.

```mermaid
flowchart LR
    Usuaria([Usuaria])

    Usuaria --> UC1[Registrar venta]
    Usuaria --> UC2[Buscar producto]
    Usuaria --> UC3[Abrir / cerrar turno de caja]
    Usuaria --> UC4[Consultar cuenta de cliente]
    Usuaria --> UC5[Administrar catálogo]
    Usuaria --> UC6[Registrar factura de compra]
    Usuaria --> UC7[Ajustar inventario]
    Usuaria --> UC8[Ver reportes de rentabilidad]

    UC5 -.include.-> UC10[Calcular margen y markup]
    UC1 -.include.-> UC11[Sincronizar con Supabase]
    UC7 -.include.-> UC11
```

## 2. Clases

Refleja el código real de `src/pos/dominio/` (no un diseño aspiracional —
arquitectura por capas, ver ADR 0001).

```mermaid
classDiagram
    class Producto {
        +str codigo
        +str nombre
        +Dinero precio
        +UnidadVenta unidad_venta
        +int categoria_id
        +bool activo
        +Costo costo
        +es_granel bool
        +margen Decimal
        +markup Decimal
        +calcular_total(cantidad) Dinero
    }
    class Dinero {
        +int monto
        +str moneda
        +desde_decimal(valor) Dinero
        +multiplicado_por(factor) Dinero
    }
    class Costo {
        +Dinero neto
        +Dinero iva
        +Dinero impuesto_adicional
        +total Dinero
    }
    class UnidadVenta {
        <<enumeration>>
        UNIDAD
        GRANEL
    }
    class Existencia {
        +str codigo_producto
        +Decimal cantidad
        +ingresar(cantidad)
        +descontar(cantidad)
    }
    class RepositorioProductos {
        <<interface>>
        +guardar(producto)
        +obtener_por_codigo(codigo) Producto
        +listar() list~Producto~
    }
    class RepositorioExistencias {
        <<interface>>
        +obtener(codigo) Existencia
        +guardar(existencia)
    }
    class RegistrarProducto {
        +repositorio RepositorioProductos
        +ejecutar(codigo, nombre, precio, ...) Producto
    }
    class AjustarStock {
        +repositorio RepositorioExistencias
        +ingresar(codigo, cantidad, motivo) Existencia
        +descontar(codigo, cantidad, motivo) Existencia
    }

    Producto "1" --> "1" Dinero : precio
    Producto "1" --> "0..1" Costo : costo
    Producto "1" --> "1" UnidadVenta
    Costo "1" --> "3" Dinero : neto/iva/adicional
    RegistrarProducto ..> RepositorioProductos : usa
    RegistrarProducto ..> Producto : crea
    AjustarStock ..> RepositorioExistencias : usa
    AjustarStock ..> Existencia : modifica
    RepositorioProductos <|.. RepositorioProductosSQLite : implementa
    RepositorioExistencias <|.. RepositorioExistenciasSQLite : implementa
```

`Producto.categoria_id` referencia la tabla `categoria` del modelo ER (§06) en vez
de guardar el nombre como texto: renombrar o fusionar categorías (HU-PRD-10) solo
debe tocar una fila de esa tabla, no reescribir cada producto que la usa.
`AjustarStock.ingresar/descontar` exigen `motivo` (HU-INV-04) — es la corrección de
los 29.715 ajustes de inventario sin causa del sistema legado.

## 3. Secuencia — Registro de una venta

Funcionalidad principal (HU-VTA-01/02). Ilustra el flujo objetivo una vez
construido el módulo de ventas sobre los casos de uso y repositorios ya existentes;
`RegistrarVenta` y `RepositorioVentas` son el trabajo de Sprint 4.

```mermaid
sequenceDiagram
    participant V as Vendedora
    participant GUI as Interfaz (Tkinter)
    participant CU as RegistrarVenta (caso de uso)
    participant RP as RepositorioProductos
    participant RE as RepositorioExistencias
    participant RV as RepositorioVentas
    participant Cola as ColaSincronizacion

    V->>GUI: escanea código de barras
    GUI->>CU: agregar_linea(codigo, cantidad)
    CU->>RP: obtener_por_codigo(codigo)
    RP-->>CU: Producto (con costo y precio)
    CU->>CU: calcular_total() / calcular ganancia (generada, no editable)
    CU-->>GUI: línea agregada al ticket

    V->>GUI: F12 Cobrar
    GUI->>CU: confirmar_venta(medios_pago)
    CU->>RE: descontar(codigo, cantidad) por cada línea
    RE-->>CU: Existencia actualizada
    CU->>RV: guardar(venta, líneas, pagos)
    RV-->>CU: venta_id
    CU->>Cola: encolar(entidad="venta", operacion="crear", id_cliente=uuid)
    Cola-->>CU: encolado (pendiente de sincronizar con Supabase)
    CU-->>GUI: venta confirmada, ticket cerrado
    GUI-->>V: muestra vuelto y opción de reimprimir
```

## 4. Componentes

```mermaid
flowchart TB
    subgraph Interfaz
        GUI[Tkinter - VentanaProductos, VentanaVenta]
    end
    subgraph Aplicacion
        CU1[Casos de uso: Registrar, Escanear,\nAjustarStock, SincronizarPendientes]
    end
    subgraph Dominio
        D1[Producto, Costo, Dinero,\nInventario, CodigoBarras]
    end
    subgraph Infraestructura
        SQLite[(SQLite local\nespejo offline)]
        Cola[Cola de sincronizacion]
        Adaptador[Adaptador Supabase]
    end
    subgraph Externo
        Supabase[(Supabase / PostgreSQL)]
    end

    GUI --> CU1
    CU1 --> D1
    CU1 --> SQLite
    CU1 --> Cola
    Cola --> Adaptador
    Adaptador -- HTTPS / TLS 1.2 --> Supabase

    style Externo fill:#f5f5f5,stroke:#999
```
