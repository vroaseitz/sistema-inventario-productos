# Diagramas de flujos de punta a punta (E2E) — Emporio NaturalSur

**Versión:** 1.0 · **Fecha:** 11-11-2026 · Estado del código: rama `develop`

Estos diagramas describen el sistema **como está construido hoy** (dos perfiles, lotes, crédito con cupo,
anulación, sincronización). Se ven directamente en GitHub (formato Mermaid). Complementan los diagramas
UML de `docs/07-diagramas-uml/` y la guía `docs/11-pruebas/guia-e2e-demo.md`.

| N° | Diagrama | Qué muestra |
|---|---|---|
| 1 | Mapa del sistema | Módulos F1–F7 y quién los usa |
| 2 | Recorrido E2E completo | Las 7 escenas de la demo, de la compra al reporte |
| 3 | Venta | Flujo de decisiones de una venta |
| 4 | Venta (secuencia) | Qué hace cada capa al cobrar |
| 5 | Jornada de caja | Estados de la jornada |
| 6 | Estados de una venta | Pagada / anulada |
| 7 | Anular una venta | Reversas de stock, crédito y caja |
| 8 | Compra con lote | De la factura al stock |
| 9 | Vencimientos y mermas | Alerta, descuento sugerido y baja |
| 10 | Crédito de clientes | Consumo, cupo, abono y estado de cuenta |
| 11 | Sincronización | Cola local → Supabase, sin internet |
| 12 | Arquitectura por capas | Dominio, aplicación, infraestructura, interfaz |
| 13 | Modelo de datos | Tablas locales y sus relaciones |
| 14 | Despliegue | Computador del local y la nube |
| 15 | Ramas e integración | Cómo llega el código a `main` |
| 16 | Niveles de prueba | Qué se prueba y con qué |

## 1. Mapa del sistema

```mermaid
flowchart LR
    V([Vendedora]) --> F1
    A([Administradora]) --> F1 & F2 & F3 & F4 & F5 & F6 & F7

    subgraph APP[Aplicación NaturalSur]
        F1[F1 Operación<br/>venta · caja y corte · resumen del día]
        F2[F2 Catálogo<br/>productos · categorías · precios]
        F3[F3 Inventario<br/>existencias · lotes · alertas · mermas]
        F4[F4 Clientes<br/>crédito · cuenta · abonos]
        F5[F5 Compras<br/>proveedores · facturas]
        F6[F6 Reportes<br/>ventas · rentabilidad · rotación]
        F7[F7 Administración<br/>usuarios · auditoría · configuración]
    end

    APP --> BD[(SQLite local)]
    BD -. cola de sincronización .-> NUBE[(Supabase / PostgreSQL)]
```

## 2. Recorrido E2E completo (las 7 escenas de la demo)

```mermaid
flowchart TD
    E1[1 · Ingreso<br/>admin crea a la vendedora<br/>la vendedora solo ve F1] --> E2
    E2[2 · Compra<br/>proveedor + factura con lote<br/>sube stock y actualiza costo] --> E3
    E3[3 · Inventario<br/>existencias, alerta de vencimiento<br/>descuento sugerido y merma] --> E4
    E4[4 · Cliente<br/>se crea el cliente con crédito] --> E5
    E5[5 · Venta<br/>abrir jornada · granel con descuento en efectivo<br/>venta a crédito] --> E6
    E6[6 · Cuenta<br/>consumo, abono y estado de cuenta<br/>con 20 % de descuento] --> E7
    E7[7 · Reportes y auditoría<br/>ventas, rentabilidad y registro de cambios]

    E2 -. lote y costo .-> E5
    E5 -. consumo a crédito .-> E6
    E5 -. ventas .-> E7
    E3 -. merma .-> E7
```

## 3. Venta — flujo de decisiones

```mermaid
flowchart TD
    I([Inicio]) --> J{¿Jornada abierta?}
    J -- No --> AJ[Abrir jornada<br/>contar el fondo] --> P
    J -- Sí --> P[Escanear código o buscar con F10]
    P --> X{¿Existe y está activo?}
    X -- No --> AV[Aviso: no existe / desactivado] --> P
    X -- Sí --> G{¿A granel?}
    G -- Sí --> KG[Pedir peso en kg] --> L
    G -- No --> L[Agregar línea<br/>lote que vence primero · F11 cambia el lote]
    L --> D{¿Descuento?}
    D -- Sí --> DM[Porcentaje o monto<br/>motivo obligatorio · queda en auditoría] --> M
    D -- No --> M{¿Más productos?}
    M -- Sí --> P
    M -- No --> C[F12 Cobrar]
    C --> MP{Medio de pago}
    MP -- Efectivo --> EF[Billetes entregados → cambio]
    MP -- Tarjeta / Transferencia --> TT[Monto]
    MP -- Crédito --> CR{¿Cliente elegido, activo<br/>y con cupo?}
    CR -- No --> RC[Aviso con el cupo disponible] --> MP
    CR -- Sí --> CC[Cargo a la cuenta]
    EF & TT & CC --> T{¿Pagos = total?}
    T -- No --> MP
    T -- Sí --> S{¿Stock suficiente?}
    S -- No --> SI[Aviso: stock insuficiente] --> P
    S -- Sí --> R[Registrar venta<br/>baja stock y lotes · encola sincronización]
    R --> TK[Imprimir ticket o solo registrar] --> F([Fin])
```

## 4. Venta — secuencia entre capas

```mermaid
sequenceDiagram
    actor U as Vendedora
    participant UI as Interfaz (app_ventas / cobro)
    participant CU as Caso de uso RegistrarVenta
    participant DOM as Dominio (Venta, Pago, Lote)
    participant BD as SQLite
    participant COLA as Cola de sincronización

    U->>UI: Escanea producto
    UI->>CU: agregar_producto(código, cantidad)
    CU->>BD: buscar producto y lotes
    CU->>DOM: agregar línea (valida activo y stock)
    U->>UI: F12 Cobrar + medio de pago
    UI->>CU: agregar_pago(pago)
    UI->>CU: cerrar(venta)
    CU->>DOM: validar pagos = total
    alt Pago con crédito
        CU->>BD: saldo y cupo del cliente
        CU-->>UI: rechazo si supera el cupo
    end
    CU->>BD: guardar venta, detalles, pagos y lotes consumidos (una transacción)
    CU->>BD: descontar existencias
    CU->>COLA: encolar operación «venta» (pending)
    CU-->>UI: venta registrada · cambio a entregar
    UI-->>U: Ticket / mensaje
```

## 5. Jornada de caja

```mermaid
stateDiagram-v2
    [*] --> SinJornada
    SinJornada --> Abierta: Abrir jornada (fondo contado)
    Abierta --> Abierta: Venta · movimiento de caja · anulación
    Abierta --> Cerrada: Hacer corte de hoy (conteo y diferencia)
    Cerrada --> [*]
    note right of Abierta
        Solo con la jornada abierta
        se puede vender o anular
    end note
```

## 6. Estados de una venta

```mermaid
stateDiagram-v2
    [*] --> EnCurso: Nuevo ticket
    EnCurso --> EnEspera: Dejar ticket en espera
    EnEspera --> EnCurso: Retomar
    EnCurso --> Pagada: Cobrar
    EnCurso --> [*]: Eliminar ticket
    Pagada --> Anulada: Anular (administradora, misma jornada, con motivo)
    Anulada --> [*]
    Pagada --> [*]
```

## 7. Anular una venta (HU-VTA-11)

```mermaid
flowchart TD
    A([Anular venta]) --> R{¿Es administradora?}
    R -- No --> N1[Aviso: solo la administradora]
    R -- Sí --> J{¿Jornada abierta y la venta<br/>es de esta jornada?}
    J -- No --> N2[Aviso: no se puede anular]
    J -- Sí --> M[Elegir la venta y escribir el motivo]
    M --> T[Una sola transacción]
    T --> S[Devuelve el stock y el saldo de los lotes]
    T --> C{¿Tenía crédito?}
    C -- Sí --> AB[Movimiento «Anulación» en la cuenta del cliente]
    T --> E[Venta queda «anulada» con motivo, autor y hora<br/>no se borra]
    T --> AU[Registro en auditoría]
    T --> Q[Operación en la cola de sincronización]
    E --> CO[El corte la muestra aparte:<br/>«Ventas anuladas»]
```

## 8. Compra con lote (F5)

```mermaid
flowchart TD
    P[Nuevo proveedor<br/>solo la primera vez] --> F[Registrar factura<br/>número, fecha, neto e impuestos]
    F --> L[Agregar línea: producto, cantidad, costo neto]
    L --> PE{¿Perecible?}
    PE -- Sí --> LO[Fecha de vencimiento y código de lote]
    PE -- No --> MAS
    LO --> MAS{¿Más líneas?}
    MAS -- Sí --> L
    MAS -- No --> CU{¿Suma del detalle = neto?}
    CU -- No --> L
    CU -- Sí --> CF[Confirmar factura]
    CF --> S1[Aumenta existencias]
    CF --> S2[Crea el lote con su saldo]
    CF --> S3[Actualiza el costo neto<br/>guarda el costo anterior]
    CF --> S4[Auditoría + cola de sincronización]
```

## 9. Vencimientos, descuento sugerido y mermas (F3)

```mermaid
flowchart LR
    LOTE[(Lotes con fecha<br/>de vencimiento)] --> CAL{Días para vencer<br/>≤ días de aviso}
    CAL -- No --> OK[Sin alerta]
    CAL -- Sí --> AL[Alerta en F3 y en<br/>Resumen del día]
    AL --> SUG[Descuento sugerido<br/>y precio rebajado]
    SUG --> DEC{Decide la administradora}
    DEC -- Vender con descuento --> VTA[Descuento a la línea en F1]
    DEC -- Ya no se puede vender --> MER[Ajustes y mermas<br/>cantidad + motivo obligatorio]
    MER --> BAJ[Baja existencias y saldo del lote<br/>queda en auditoría]
```

El descuento es una **sugerencia**: el sistema no cambia el precio solo.

## 10. Crédito de clientes (F4)

```mermaid
sequenceDiagram
    actor A as Administradora
    actor V as Vendedora
    participant S as Sistema
    participant CTA as Cuenta del cliente

    A->>S: Nuevo cliente (cupo opcional)
    V->>S: Venta con «Crédito cliente»
    S->>CTA: ¿saldo + venta ≤ cupo?
    alt Supera el cupo
        S-->>V: Rechazo con el cupo disponible
    else Dentro del cupo o sin límite
        S->>CTA: Consumo (cargo)
    end
    A->>S: Registrar abono (monto, medio)
    S->>CTA: Abono
    A->>S: Estado de cuenta del ciclo (mes)
    S-->>A: Consumos − 20 % crédito familiar = total a pagar · abonos · saldo final
```

## 11. Sincronización sin internet (offline-first)

```mermaid
flowchart TD
    OP[Operación en el local<br/>venta, abono, compra, merma, anulación…] --> TX[Se guarda en SQLite<br/>y en la cola, en la misma transacción]
    TX --> PEND[(cola_sincronizacion<br/>estado «pending»)]
    PEND --> INT{¿Hay internet y<br/>Supabase configurado?}
    INT -- No --> ESP[Se sigue trabajando<br/>la barra muestra «Pendientes: N»] --> INT
    INT -- Sí --> TRA[Traductor: operación → SQL del esquema «pos»]
    TRA --> PUB[Publicar en Supabase]
    PUB --> OKQ{¿Resultó?}
    OKQ -- Sí --> SYN[Marca «synced»] --> PEND
    OKQ -- No --> COR[Se detiene: lo enviado queda «synced»,<br/>el resto sigue «pending» y se reintenta]
    COR --> INT
```

Cada operación lleva un identificador único del cliente, así un reintento **no duplica** datos en la nube.

## 12. Arquitectura por capas (hexagonal)

```mermaid
flowchart TB
    subgraph INTERFAZ[Interfaz · Tkinter]
        VP[ventana_principal] --> PANT[app_ventas · app_catalogo · app_inventario<br/>app_clientes · app_compras · app_reportes · app_administracion]
    end
    subgraph APLICACION[Aplicación]
        CU[Casos de uso<br/>registrar_venta · anular_venta · registrar_factura_compra<br/>registrar_merma · gestionar_clientes · sincronizar_pendientes …]
        PU[Puertos<br/>repositorios · ColaSincronizacion · PublicadorRemoto]
    end
    subgraph DOMINIO[Dominio · reglas puras]
        DM[ventas · caja · clientes · inventario · productos · formato]
    end
    subgraph INFRA[Infraestructura]
        SQ[sqlite · repositorios y esquema]
        SB[supabase · adaptador y traductor]
        IM[impresion · comprobante y cajón]
        SE[seguridad · claves con hash]
    end
    PANT --> CU
    CU --> DM
    CU --> PU
    SQ -. implementa .-> PU
    SB -. implementa .-> PU
    IM -. implementa .-> PU
    SE -. implementa .-> PU
```

El dominio no conoce ni la base de datos ni la pantalla; por eso se prueba sin ellas.

## 13. Modelo de datos local (SQLite)

Se muestran las tablas principales y sus campos clave; el detalle está en `docs/06-modelo-datos/`.

```mermaid
erDiagram
    CATEGORIAS ||--o{ PRODUCTOS : agrupa
    PRODUCTOS ||--|| EXISTENCIAS : tiene
    PRODUCTOS ||--o{ LOTES : "se recibe en"
    PRODUCTOS ||--o{ HISTORIAL_PRECIOS : registra
    PRODUCTOS ||--o{ MOVIMIENTOS_INVENTARIO : registra
    USUARIOS ||--o{ TURNOS_CAJA : abre
    TURNOS_CAJA ||--o{ VENTAS : contiene
    TURNOS_CAJA ||--o{ MOVIMIENTOS_CAJA : contiene
    VENTAS ||--|{ VENTA_DETALLES : incluye
    VENTAS ||--|{ VENTA_PAGOS : "se paga con"
    VENTAS ||--o{ VENTA_LOTES : consume
    LOTES ||--o{ VENTA_LOTES : "sale de"
    PRODUCTOS ||--o{ VENTA_DETALLES : "se vende en"
    CLIENTES ||--o{ VENTAS : "compra a crédito"
    CLIENTES ||--o{ MOVIMIENTOS_CLIENTE : "consumos y abonos"
    PROVEEDORES ||--o{ FACTURAS_COMPRA : emite
    FACTURAS_COMPRA ||--|{ FACTURAS_COMPRA_LINEAS : detalla
    PRODUCTOS ||--o{ FACTURAS_COMPRA_LINEAS : "se compra en"

    PRODUCTOS {
        text codigo PK
        text nombre
        int precio
        int costo_neto
        text unidad_venta
        bool perecible
        bool activo
    }
    LOTES {
        text uuid
        text codigo_producto FK
        date fecha_vencimiento
        real saldo
    }
    VENTAS {
        int id PK
        text uuid
        int turno_caja_id FK
        int cliente_id
        text estado
        text motivo_anulacion
    }
    VENTA_PAGOS {
        int venta_id FK
        text medio_pago
        int monto
        int monto_entregado
    }
    CLIENTES {
        int id PK
        text nombre
        int cupo
        bool activo
    }
    MOVIMIENTOS_CLIENTE {
        int cliente_id FK
        text tipo
        int monto
        text medio
        text venta_uuid
    }
    TURNOS_CAJA {
        int id PK
        int usuario_id
        int fondo_inicial
        datetime abierto_en
        datetime cerrado_en
    }
```

Tablas de apoyo sin relación directa: `auditoria`, `configuracion`, `tickets_en_espera`,
`historial_ajustes_inventario` y `cola_sincronizacion`.

## 14. Despliegue

```mermaid
flowchart LR
    subgraph LOCAL[Computador del local · Windows 8.1 de 64 bits]
        EXE[pos-naturalsur.exe<br/>empaquetado con PyInstaller]
        DB[(pos_local.db<br/>SQLite)]
        EXE --> DB
    end
    LECTOR[Lector de código<br/>de barras] --> EXE
    EXE --> IMP[Impresora térmica<br/>y cajón]
    EXE -. internet, cuando hay .-> SUP[(Supabase<br/>PostgreSQL · esquema «pos»)]
    DEV[Equipo de desarrollo<br/>GitHub] -. compila en VM Windows 8.1 .-> EXE
```

Pendiente de verificar con el equipo real: la impresora térmica (ver `checklist-de-termino.md`).

## 15. Ramas e integración

```mermaid
flowchart LR
    FF[feat/… y fix/…<br/>ramas de Fernando] --> DP[feat/diseno-prototipo]
    ED[fix/pr3-conflictos-main<br/>rama de Eduardo] --> DEV
    DP --> DEV[develop<br/>rama de desarrollo unificada]
    MA0[main<br/>minuta N°3] --> DEV
    DEV == PR con aprobación del otro desarrollador ==> MAIN[main<br/>lo que extrae la Dirección de Carrera]
```

Estado al 11-11-2026: `develop` contiene todas las ramas; falta el PR `develop → main`.

## 16. Niveles de prueba

```mermaid
flowchart TB
    M[Aceptación manual · QA<br/>recorridos con la app real, 6 ciclos] --> E
    E[Interfaz E2E<br/>la app Tkinter real, un proceso por escenario] --> I
    I[Integración<br/>casos de uso con SQLite real y PostgreSQL en Docker] --> U
    U[Unitarias<br/>reglas del dominio]
    S[Seguridad y rendimiento] --- I
```

Resultados y casos: `docs/11-pruebas/casos-de-prueba.md`.
