"""Traduce operaciones de la cola de sincronizacion a sentencias SQL de PostgreSQL.

Se separa del adaptador para poder probar el mapeo entidad -> sentencias SIN psycopg2 ni
credenciales. El adaptador solo ejecuta lo que este traductor construye.

Destino: schema `pos` (database/migraciones/002 a 004). Todas las sentencias son
idempotentes: reintentar una operacion tras un corte no duplica ni corrompe datos.

- producto / existencia / lote: upsert por `producto.codigo` (codigo interno) o por UUID (lote).
- turno_abrir / turno_cerrar / movimiento_caja / venta: el UUID generado en el cliente
  se guarda como `id_cliente` (UNIQUE) y `ON CONFLICT DO NOTHING` absorbe el reintento.
  La venta con sus lineas y pagos va en UNA sola sentencia (CTE), asi que o entra
  completa o no entra, y un reintento no duplica lineas.

Los ids numericos locales (SQLite) y remotos (IDENTITY) son independientes; el enlace
es el UUID o el codigo. Mientras no exista inicio de sesion, el usuario remoto es la
cuenta tecnica `caja@naturalsur.local` (migracion 004).
"""

from __future__ import annotations

Sentencia = tuple[str, tuple]

_USUARIO_CAJA = "(SELECT id FROM pos.usuario WHERE correo = 'caja@naturalsur.local')"
_CATEGORIA_DEFECTO = "(SELECT id FROM pos.categoria WHERE nombre = 'Sin categoria')"

_SQL_PRODUCTO = (
    "INSERT INTO pos.producto (codigo, nombre, categoria_id, unidad_venta, precio_venta, activo) "
    f"VALUES (%s, %s, {_CATEGORIA_DEFECTO}, %s, %s, %s) "
    "ON CONFLICT (codigo) DO UPDATE SET "
    "nombre = EXCLUDED.nombre, unidad_venta = EXCLUDED.unidad_venta, "
    "precio_venta = EXCLUDED.precio_venta, activo = EXCLUDED.activo"
)

_SQL_CATEGORIA = "INSERT INTO pos.categoria (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING"

_SQL_PRODUCTO_CON_CATEGORIA = (
    "INSERT INTO pos.producto (codigo, nombre, categoria_id, unidad_venta, precio_venta, activo) "
    "VALUES (%s, %s, (SELECT id FROM pos.categoria WHERE nombre = %s), %s, %s, %s) "
    "ON CONFLICT (codigo) DO UPDATE SET "
    "nombre = EXCLUDED.nombre, categoria_id = EXCLUDED.categoria_id, "
    "unidad_venta = EXCLUDED.unidad_venta, "
    "precio_venta = EXCLUDED.precio_venta, activo = EXCLUDED.activo"
)

_SQL_EXISTENCIA = (
    "INSERT INTO pos.existencia (producto_id, cantidad) "
    "SELECT p.id, %s::numeric FROM pos.producto p WHERE p.codigo = %s "
    "ON CONFLICT (producto_id) DO UPDATE SET cantidad = EXCLUDED.cantidad"
)

_SQL_TURNO_ABRIR = (
    "INSERT INTO pos.turno_caja (id_cliente, usuario_id, fondo_inicial, abierto_en) "
    f"VALUES (%s, {_USUARIO_CAJA}, %s, %s::timestamptz) "
    "ON CONFLICT (id_cliente) DO NOTHING"
)

_SQL_TURNO_CERRAR = (
    "UPDATE pos.turno_caja SET cerrado_en = %s::timestamptz "
    "WHERE id_cliente = %s AND cerrado_en IS NULL"
)

_SQL_MOVIMIENTO = (
    "INSERT INTO pos.movimiento_caja (id_cliente, turno_caja_id, tipo, monto, motivo, creado_en) "
    "SELECT %s, t.id, %s, %s, %s, %s::timestamptz FROM pos.turno_caja t WHERE t.id_cliente = %s "
    "ON CONFLICT (id_cliente) DO NOTHING"
)


_SQL_LOTE = (
    "INSERT INTO pos.lote (id_cliente, producto_id, fecha_vencimiento, saldo) "
    "SELECT %s, p.id, %s::date, %s::numeric FROM pos.producto p WHERE p.codigo = %s "
    "ON CONFLICT (id_cliente) DO UPDATE SET "
    "saldo = EXCLUDED.saldo, fecha_vencimiento = EXCLUDED.fecha_vencimiento"
)


def _sql_venta(n_lineas: int, n_pagos: int) -> str:
    linea = "(%s::text, %s::numeric, %s::numeric, %s::numeric, %s::numeric)"
    lineas = ", ".join([linea] * n_lineas)
    pagos = ", ".join(["(%s::text, %s::numeric)"] * n_pagos)
    return (
        "WITH v AS ("
        "INSERT INTO pos.venta (id_cliente, turno_caja_id, usuario_id, estado, creado_en) "
        f"SELECT %s, t.id, {_USUARIO_CAJA}, %s, %s::timestamptz "
        "FROM pos.turno_caja t WHERE t.id_cliente = %s "
        "ON CONFLICT (id_cliente) DO NOTHING RETURNING id), "
        "d AS ("
        "INSERT INTO pos.venta_detalle "
        "(venta_id, producto_id, cantidad, precio_unitario, costo_unitario, descuento_linea) "
        "SELECT v.id, p.id, x.cantidad, x.precio, x.costo, x.descuento "
        f"FROM v CROSS JOIN (VALUES {lineas}) AS x(codigo, cantidad, precio, costo, descuento) "
        "JOIN pos.producto p ON p.codigo = x.codigo RETURNING 1) "
        "INSERT INTO pos.venta_pago (venta_id, medio_pago, monto) "
        f"SELECT v.id, y.medio, y.monto FROM v CROSS JOIN (VALUES {pagos}) AS y(medio, monto)"
    )


def traducir_operacion(operacion: dict) -> list[Sentencia]:
    """Devuelve las sentencias (sql, params) que aplican `operacion` en Supabase.

    Lanza ValueError si la entidad no esta soportada. `operacion` tiene la forma que
    entrega la cola: {entidad, operacion, datos, id_cliente}.
    """
    entidad = operacion["entidad"]
    d = operacion["datos"]

    if entidad == "producto" and d.get("categoria"):
        return [
            (_SQL_CATEGORIA, (d["categoria"],)),
            (
                _SQL_PRODUCTO_CON_CATEGORIA,
                (
                    d["codigo"],
                    d["nombre"],
                    d["categoria"],
                    str(d["unidad_venta"]).upper(),
                    d["precio"],
                    d.get("activo", True),
                ),
            ),
        ]

    if entidad == "producto":
        return [
            (
                _SQL_PRODUCTO,
                (
                    d["codigo"],
                    d["nombre"],
                    str(d["unidad_venta"]).upper(),
                    d["precio"],
                    d.get("activo", True),
                ),
            )
        ]

    if entidad == "existencia":
        return [(_SQL_EXISTENCIA, (d["cantidad"], d["codigo_producto"]))]

    if entidad == "lote":
        return [(_SQL_LOTE, (d["uuid"], d["fecha_vencimiento"], d["saldo"], d["codigo_producto"]))]

    if entidad == "turno_abrir":
        return [(_SQL_TURNO_ABRIR, (d["uuid"], d["fondo_inicial"], d["abierto_en"]))]

    if entidad == "turno_cerrar":
        return [(_SQL_TURNO_CERRAR, (d["cerrado_en"], d["uuid"]))]

    if entidad == "movimiento_caja":
        return [
            (
                _SQL_MOVIMIENTO,
                (
                    operacion["id_cliente"],
                    d["tipo"],
                    d["monto"],
                    d["motivo"],
                    d["creado_en"],
                    d["turno_uuid"],
                ),
            )
        ]

    if entidad == "venta":
        lineas, pagos = d["detalles"], d["pagos"]
        if not lineas or not pagos:
            raise ValueError("Una venta sincronizable requiere al menos una linea y un pago")
        params: list = [d["uuid"], d["estado"], d["creado_en"], d["turno_uuid"]]
        for linea in lineas:
            params += [
                linea["codigo"],
                linea["cantidad"],
                linea["precio"],
                linea.get("costo"),
                linea.get("descuento", 0),
            ]
        for pago in pagos:
            params += [pago["medio"], pago["monto"]]
        return [(_sql_venta(len(lineas), len(pagos)), tuple(params))]

    raise ValueError(f"Entidad no soportada para sincronizacion: {entidad!r}")
