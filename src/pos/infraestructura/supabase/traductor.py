"""Traduce operaciones de la cola de sincronizacion a sentencias SQL de PostgreSQL.

Se separa del adaptador para poder probar el mapeo entidad -> sentencia SIN psycopg2 ni
credenciales. El adaptador solo ejecuta lo que este traductor construye.

Cada sentencia es idempotente en el destino (ON CONFLICT sobre la clave de negocio),
de modo que reintentar una operacion no duplica ni corrompe datos.
"""

from __future__ import annotations

# Placeholders con estilo psycopg2 (%s). Las sentencias aplican la operacion a las
# TABLAS DE NEGOCIO (no a la cola): esa es la diferencia con un simple volcado de la cola.
_SQL_PRODUCTO = (
    "INSERT INTO productos (codigo, nombre, precio, unidad_venta, categoria, activo) "
    "VALUES (%s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (codigo) DO UPDATE SET "
    "nombre = EXCLUDED.nombre, precio = EXCLUDED.precio, "
    "unidad_venta = EXCLUDED.unidad_venta, categoria = EXCLUDED.categoria, "
    "activo = EXCLUDED.activo"
)

_SQL_EXISTENCIA = (
    "INSERT INTO existencias (codigo_producto, cantidad) VALUES (%s, %s) "
    "ON CONFLICT (codigo_producto) DO UPDATE SET cantidad = EXCLUDED.cantidad"
)


def traducir_operacion(operacion: dict) -> tuple[str, tuple]:
    """Devuelve (sql, params) para aplicar `operacion` en PostgreSQL/Supabase.

    Lanza ValueError si la entidad no esta soportada. `operacion` tiene la forma que
    entrega la cola: {entidad, operacion, datos, id_cliente}.
    """
    entidad = operacion["entidad"]
    datos = operacion["datos"]

    if entidad == "producto":
        params = (
            datos["codigo"],
            datos["nombre"],
            datos["precio"],
            datos["unidad_venta"],
            datos.get("categoria"),
            datos.get("activo", True),
        )
        return _SQL_PRODUCTO, params

    if entidad == "existencia":
        params = (datos["codigo_producto"], datos["cantidad"])
        return _SQL_EXISTENCIA, params

    raise ValueError(f"Entidad no soportada para sincronizacion: {entidad!r}")
