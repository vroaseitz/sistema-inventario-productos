# ADR 0002 — Operación sin conexión a internet (offline)

- **Estado:** Aceptado
- **Fecha:** 2026-08-24
- **Decisores:** Equipo Capstone (Fernando Silva — desarrollo)

## Contexto

El sistema legacy usa Firebird **embebido y local**: el local vende **sin depender de
internet**. El sistema nuevo usa Supabase (PostgreSQL) **en la nube**. Si la app hablara
solo con la nube, un corte de internet dejaría a la tienda **sin poder vender**. Eso es
una **regresión** frente al sistema actual y es inaceptable para el negocio (Germaine, una
de las dueñas, ya desconfía de los cambios de sistema).

## Opciones

1. **Solo-online:** la app escribe directo a Supabase. Simple, pero si se cae internet no
   se vende. Regresión. **Descartada.**
2. **Espejo local + cola de sincronización:** la app opera contra una base **SQLite
   local** (fuente de verdad operativa en el local) y **encola** los cambios para
   sincronizarlos con Supabase cuando hay red. **Elegida.**
3. Base local completa con replicación bidireccional automática: potente pero compleja y
   arriesgada para el alcance y el plazo del proyecto. Descartada por ahora.

## Decisión

**Espejo local SQLite + cola de sincronización idempotente hacia Supabase.**

### Modelo de sincronización

- La app **siempre** lee y escribe en SQLite local (ver `infraestructura/sqlite`). Nunca
  se bloquea por falta de red.
- Cada operación relevante (venta, ajuste de stock, alta de producto) se **encola** en la
  tabla `cola_sincronizacion` con un **UUID de cliente** (`id_cliente`) y estado
  `pending`.
- Un proceso de sincronización (`SincronizarPendientes`) publica las pendientes a Supabase
  cuando hay conexión, usando **`ON CONFLICT (id_cliente) DO NOTHING`** en el destino.
- SQLite corre en modo **WAL** con `synchronous=NORMAL`: las transacciones son atómicas y
  la base es recuperable ante un corte de energía.

### Estados de una operación

`pending` → (publicada con éxito) → `synced`
`pending` → (falla de red) → sigue `pending` (se reintenta después)

### Política de conflictos e idempotencia

- La **idempotencia por `id_cliente`** garantiza que reintentar no duplica datos: si una
  operación ya llegó al destino, el segundo intento no inserta nada.
- Un **corte a mitad de la sincronización** no pierde ni duplica: lo ya publicado quedó
  `synced`, lo pendiente sigue `pending`, y el reintento procesa solo lo pendiente. Este
  escenario está cubierto por la prueba
  `tests/integracion/test_cola_sincronizacion.py::test_corte_a_mitad_no_pierde_ni_duplica`.

### Folios / correlativos de venta offline

Para evitar choques de correlativos cuando el local vende offline, cada venta lleva un
**identificador de cliente (UUID)** además del folio legible. El folio definitivo/único
lo puede asignar el destino al sincronizar; el UUID mantiene la trazabilidad y evita
duplicados. (Detalle a implementar junto con el módulo de ventas.)

## Alcance mínimo demostrable (semana 14)

- Registrar una venta/alta con la red desconectada → queda en SQLite y en la cola.
- Reconectar → `SincronizarPendientes` sube lo pendiente a Supabase sin duplicar.
- Demostrar el caso de corte a mitad (ya cubierto por prueba automatizada).

El **modelo de datos ya queda preparado** para esto aunque la sincronización real contra
Supabase se termine después: la cola, los estados y la idempotencia están implementados y
probados; el adaptador Supabase (`infraestructura/supabase`) está listo y solo requiere
credenciales.

## Consecuencias

- **Positivas:** la tienda nunca queda sin vender; los datos no se corrompen ni duplican.
- **Negativas / a gestionar:** hay que mantener el espejo local y su esquema en sincronía
  con el de Supabase (`database/migraciones/`), y definir bien qué es la fuente de verdad
  para cada dato (operación diaria = local; consolidado = nube).
