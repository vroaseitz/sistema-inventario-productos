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

_COLUMNAS_EXTRA = "costo_neto, costo_cargado, es_perecible, dias_aviso_vencimiento, stock_minimo"
_ACTUALIZAR_EXTRA = (
    "costo_neto = EXCLUDED.costo_neto, costo_cargado = EXCLUDED.costo_cargado, "
    "es_perecible = EXCLUDED.es_perecible, "
    "dias_aviso_vencimiento = EXCLUDED.dias_aviso_vencimiento, "
    "stock_minimo = EXCLUDED.stock_minimo"
)

_SQL_PRODUCTO = (
    "INSERT INTO pos.producto (codigo, nombre, categoria_id, unidad_venta, precio_venta, activo, "
    f"{_COLUMNAS_EXTRA}) "
    f"VALUES (%s, %s, {_CATEGORIA_DEFECTO}, %s, %s, %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (codigo) DO UPDATE SET "
    "nombre = EXCLUDED.nombre, unidad_venta = EXCLUDED.unidad_venta, "
    f"precio_venta = EXCLUDED.precio_venta, activo = EXCLUDED.activo, {_ACTUALIZAR_EXTRA}"
)

# Cambio de codigo de barras (CA-19): renombra el producto existente; si el codigo nuevo ya existe
# no hace nada (el reintento tras un corte es inofensivo).
_SQL_PRODUCTO_CODIGO = (
    "UPDATE pos.producto SET codigo = %s WHERE codigo = %s "
    "AND NOT EXISTS (SELECT 1 FROM pos.producto WHERE codigo = %s)"
)

_SQL_CATEGORIA = "INSERT INTO pos.categoria (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING"

_SQL_CATEGORIA_ESTADO = (
    "INSERT INTO pos.categoria (nombre, activa) VALUES (%s, %s) "
    "ON CONFLICT (nombre) DO UPDATE SET activa = EXCLUDED.activa"
)

# Renombrar: solo si el nombre nuevo no existe ya (si existiera, la fusion trae los productos).
_SQL_CATEGORIA_RENOMBRAR = (
    "UPDATE pos.categoria SET nombre = %s WHERE nombre = %s "
    "AND NOT EXISTS (SELECT 1 FROM pos.categoria WHERE nombre = %s)"
)

# Eliminar (despues de fusionar): nunca borra una categoria que aun tenga productos.
_SQL_CATEGORIA_ELIMINAR = (
    "DELETE FROM pos.categoria c WHERE c.nombre = %s "
    "AND NOT EXISTS (SELECT 1 FROM pos.producto p WHERE p.categoria_id = c.id)"
)

_SQL_PRODUCTO_CON_CATEGORIA = (
    "INSERT INTO pos.producto (codigo, nombre, categoria_id, unidad_venta, precio_venta, activo, "
    f"{_COLUMNAS_EXTRA}) "
    "VALUES (%s, %s, (SELECT id FROM pos.categoria WHERE nombre = %s), %s, %s, %s, "
    "%s, %s, %s, %s, %s) "
    "ON CONFLICT (codigo) DO UPDATE SET "
    "nombre = EXCLUDED.nombre, categoria_id = EXCLUDED.categoria_id, "
    "unidad_venta = EXCLUDED.unidad_venta, "
    f"precio_venta = EXCLUDED.precio_venta, activo = EXCLUDED.activo, {_ACTUALIZAR_EXTRA}"
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
    "INSERT INTO pos.lote (id_cliente, producto_id, fecha_vencimiento, saldo, codigo_lote) "
    "SELECT %s, p.id, %s::date, %s::numeric, %s FROM pos.producto p WHERE p.codigo = %s "
    "ON CONFLICT (id_cliente) DO UPDATE SET "
    "saldo = EXCLUDED.saldo, fecha_vencimiento = EXCLUDED.fecha_vencimiento, "
    "codigo_lote = EXCLUDED.codigo_lote"
)


# --- Clientes, credito, proveedores, facturas de compra y auditoria (migracion 008) ---------

_SQL_CLIENTE = (
    "INSERT INTO pos.cliente (id_cliente, nombre, tiene_credito, telefono, correo, "
    "observaciones, activo) VALUES (%s, %s, TRUE, %s, %s, %s, %s) "
    "ON CONFLICT (id_cliente) DO UPDATE SET nombre = EXCLUDED.nombre, "
    "telefono = EXCLUDED.telefono, correo = EXCLUDED.correo, "
    "observaciones = EXCLUDED.observaciones, activo = EXCLUDED.activo"
)

# El consumo local es un «cargo» en el destino. Si la venta aun no llego, venta_id queda vacio.
_SQL_MOVIMIENTO_CLIENTE = (
    "INSERT INTO pos.movimiento_credito "
    "(id_cliente, cliente_id, venta_id, tipo, monto, creado_en, medio, detalle) "
    "SELECT %s, c.id, (SELECT v.id FROM pos.venta v WHERE v.id_cliente = %s), "
    "%s, %s, %s::timestamptz, %s, %s FROM pos.cliente c WHERE c.id_cliente = %s "
    "ON CONFLICT (id_cliente) DO NOTHING"
)

_SQL_PROVEEDOR = (
    "INSERT INTO pos.proveedor (nombre, contacto) VALUES (%s, %s) "
    "ON CONFLICT (lower(nombre)) DO UPDATE SET contacto = EXCLUDED.contacto"
)

# Para una factura: el proveedor tiene que existir, pero no se le pisa el contacto.
_SQL_PROVEEDOR_SI_FALTA = (
    "INSERT INTO pos.proveedor (nombre) VALUES (%s) ON CONFLICT (lower(nombre)) DO NOTHING"
)

_SQL_AUDITORIA = (
    "INSERT INTO pos.auditoria (id_cliente, tabla, registro_id, usuario_nombre, accion, "
    "datos_antes, datos_despues, detalle, creado_en) "
    "VALUES (%s, 'app', %s, %s, %s, to_jsonb(%s::text), to_jsonb(%s::text), %s, %s::timestamptz) "
    "ON CONFLICT (id_cliente) DO NOTHING"
)


def _sql_factura(n_lineas: int) -> str:
    """La factura y todas sus lineas en UNA sentencia: entra completa o no entra, y reintentar no
    duplica (la clave es proveedor + numero)."""
    linea = "(%s::text, %s::numeric, %s::numeric, %s::numeric, %s::date, %s::text)"
    lineas = ", ".join([linea] * n_lineas)
    return (
        "WITH f AS ("
        "INSERT INTO pos.factura_compra "
        "(proveedor_id, numero_factura, fecha, monto_neto, monto_impuestos, estado) "
        "SELECT p.id, %s, %s::date, %s, %s, %s FROM pos.proveedor p "
        "WHERE lower(p.nombre) = lower(%s) "
        "ON CONFLICT (proveedor_id, numero_factura) DO NOTHING RETURNING id) "
        "INSERT INTO pos.factura_compra_detalle "
        "(factura_id, producto_id, cantidad, costo_unitario_neto, costo_anterior, "
        "fecha_vencimiento, codigo_lote) "
        "SELECT f.id, p.id, x.cantidad, x.costo, x.anterior, x.vence, x.lote FROM f CROSS JOIN "
        f"(VALUES {lineas}) AS x(codigo, cantidad, costo, anterior, vence, lote) "
        "JOIN pos.producto p ON p.codigo = x.codigo"
    )


def _params_cliente(c: dict) -> tuple:
    return (
        c["id"],
        c["nombre"],
        c.get("telefono") or "",
        c.get("correo") or "",
        c.get("observaciones") or "",
        c.get("activo", True),
    )


def _sql_venta(n_lineas: int, n_pagos: int) -> str:
    linea = "(%s::text, %s::numeric, %s::numeric, %s::numeric, %s::numeric, %s::text)"
    lineas = ", ".join([linea] * n_lineas)
    pagos = ", ".join(["(%s::text, %s::numeric)"] * n_pagos)
    return (
        "WITH v AS ("
        "INSERT INTO pos.venta (id_cliente, turno_caja_id, usuario_id, estado, creado_en, nota) "
        f"SELECT %s, t.id, {_USUARIO_CAJA}, %s, %s::timestamptz, %s "
        "FROM pos.turno_caja t WHERE t.id_cliente = %s "
        "ON CONFLICT (id_cliente) DO NOTHING RETURNING id), "
        "d AS ("
        "INSERT INTO pos.venta_detalle "
        "(venta_id, producto_id, cantidad, precio_unitario, costo_unitario, descuento_linea, "
        "motivo_descuento) "
        "SELECT v.id, p.id, x.cantidad, x.precio, x.costo, x.descuento, x.motivo "
        "FROM v CROSS JOIN "
        f"(VALUES {lineas}) AS x(codigo, cantidad, precio, costo, descuento, motivo) "
        "JOIN pos.producto p ON p.codigo = x.codigo RETURNING 1) "
        "INSERT INTO pos.venta_pago (venta_id, medio_pago, monto) "
        f"SELECT v.id, y.medio, y.monto FROM v CROSS JOIN (VALUES {pagos}) AS y(medio, monto)"
    )


def _extras_producto(d: dict) -> tuple:
    """costo_neto, costo_cargado, es_perecible, dias_aviso, stock_minimo (con valores por defecto
    para operaciones viejas que aun esten en la cola sin estos campos)."""
    costo = d.get("costo")
    return (
        costo,
        costo is not None,
        bool(d.get("perecible", False)),
        d.get("dias_aviso"),
        d.get("stock_minimo"),
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
                    *_extras_producto(d),
                ),
            ),
        ]

    if entidad == "producto_codigo":
        return [(_SQL_PRODUCTO_CODIGO, (d["nuevo"], d["anterior"], d["nuevo"]))]

    if entidad == "categoria":
        return [(_SQL_CATEGORIA_ESTADO, (d["nombre"], d.get("activa", True)))]

    if entidad == "categoria_renombrar":
        return [(_SQL_CATEGORIA_RENOMBRAR, (d["nuevo"], d["anterior"], d["nuevo"]))]

    if entidad == "categoria_eliminar":
        return [(_SQL_CATEGORIA_ELIMINAR, (d["nombre"],))]

    if entidad == "cliente":
        return [(_SQL_CLIENTE, _params_cliente(d))]

    if entidad == "movimiento_cliente":
        return [
            (_SQL_CLIENTE, _params_cliente(d["cliente"])),
            (
                _SQL_MOVIMIENTO_CLIENTE,
                (
                    d["uuid"],
                    d.get("venta_uuid"),
                    "cargo" if d["tipo"] == "consumo" else d["tipo"],
                    d["monto"],
                    d["fecha"],
                    d.get("medio"),
                    d.get("detalle") or "",
                    d["cliente"]["id"],
                ),
            ),
        ]

    if entidad == "proveedor":
        return [(_SQL_PROVEEDOR, (d["nombre"], d.get("contacto") or ""))]

    if entidad == "factura_compra":
        lineas = d["lineas"]
        if not lineas:
            raise ValueError("Una factura sincronizable requiere al menos una linea")
        params: list = [
            d["numero"],
            d["fecha"],
            d["neto"],
            d["impuestos"],
            d.get("estado", "confirmada"),
            d["proveedor"],
        ]
        for linea in lineas:
            params += [
                linea["codigo"],
                linea["cantidad"],
                linea["costo"],
                linea.get("costo_anterior"),
                linea.get("vence"),
                linea.get("lote") or "",
            ]
        return [
            (_SQL_PROVEEDOR_SI_FALTA, (d["proveedor"],)),
            (_sql_factura(len(lineas)), tuple(params)),
        ]

    if entidad == "auditoria":
        return [
            (
                _SQL_AUDITORIA,
                (
                    d["id"],
                    d.get("registro") or "",
                    d["usuario"],
                    d["accion"],
                    d.get("antes") or "",
                    d.get("despues") or "",
                    d.get("detalle") or "",
                    d["fecha"],
                ),
            )
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
                    *_extras_producto(d),
                ),
            )
        ]

    if entidad == "existencia":
        return [(_SQL_EXISTENCIA, (d["cantidad"], d["codigo_producto"]))]

    if entidad == "lote":
        return [
            (
                _SQL_LOTE,
                (
                    d["uuid"],
                    d["fecha_vencimiento"],
                    d["saldo"],
                    d.get("codigo_lote") or None,
                    d["codigo_producto"],
                ),
            )
        ]

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
        params: list = [
            d["uuid"],
            d["estado"],
            d["creado_en"],
            d.get("nota") or None,
            d["turno_uuid"],
        ]
        for linea in lineas:
            params += [
                linea["codigo"],
                linea["cantidad"],
                linea["precio"],
                linea.get("costo"),
                linea.get("descuento", 0),
                linea.get("motivo_descuento") or None,
            ]
        for pago in pagos:
            params += [pago["medio"], pago["monto"]]
        return [(_sql_venta(len(lineas), len(pagos)), tuple(params))]

    raise ValueError(f"Entidad no soportada para sincronizacion: {entidad!r}")
