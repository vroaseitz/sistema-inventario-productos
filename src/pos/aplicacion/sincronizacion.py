"""Encolado de operaciones para sincronizar con Supabase (ADR 0002).

Los casos de uso llaman a estas funciones tras escribir en SQLite. Todas son
opcionales: si no hay cola (`None`), no hacen nada, asi que el sistema funciona igual
sin Supabase configurado.

Identificadores: lo que ocurre UNA sola vez (abrir/cerrar turno, una venta) usa un id
deterministico, asi la cola absorbe un doble encolado. Lo que puede repetirse
(un producto que se edita, el stock que cambia) usa un UUID nuevo por operacion.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from pos.aplicacion.puertos import ColaSincronizacion
from pos.dominio.caja import MovimientoCaja, TurnoCaja
from pos.dominio.inventario import Existencia
from pos.dominio.lotes import Lote
from pos.dominio.productos import Producto
from pos.dominio.ventas import Venta


def encolar_producto(
    cola: ColaSincronizacion | None, producto: Producto, categoria: str | None = None
) -> None:
    if cola is None:
        return
    cola.encolar(
        "producto",
        "upsert",
        {
            "codigo": producto.codigo,
            "nombre": producto.nombre,
            "precio": producto.precio.monto,
            "unidad_venta": producto.unidad_venta.value,
            "activo": producto.activo,
            # Nombre (no id local): el id de la categoria cambia entre la base local y la remota.
            "categoria": categoria,
        },
        str(uuid4()),
    )


def encolar_existencia(cola: ColaSincronizacion | None, existencia: Existencia) -> None:
    if cola is None:
        return
    cola.encolar(
        "existencia",
        "upsert",
        {"codigo_producto": existencia.codigo_producto, "cantidad": str(existencia.cantidad)},
        str(uuid4()),
    )


def encolar_turno_abierto(cola: ColaSincronizacion | None, turno: TurnoCaja) -> None:
    if cola is None:
        return
    cola.encolar(
        "turno_abrir",
        "insert",
        {
            "uuid": turno.uuid,
            "fondo_inicial": turno.fondo_inicial.monto,
            "abierto_en": turno.abierto_en.isoformat(),
        },
        f"turno-abrir:{turno.uuid}",
    )


def encolar_turno_cerrado(cola: ColaSincronizacion | None, turno: TurnoCaja) -> None:
    if cola is None or turno.cerrado_en is None:
        return
    cola.encolar(
        "turno_cerrar",
        "update",
        {"uuid": turno.uuid, "cerrado_en": turno.cerrado_en.isoformat()},
        f"turno-cerrar:{turno.uuid}",
    )


def encolar_movimiento(
    cola: ColaSincronizacion | None, turno: TurnoCaja, movimiento: MovimientoCaja
) -> None:
    if cola is None:
        return
    cola.encolar(
        "movimiento_caja",
        "insert",
        {
            "turno_uuid": turno.uuid,
            "tipo": movimiento.tipo.value,
            "monto": movimiento.monto.monto,
            "motivo": movimiento.motivo,
            "creado_en": movimiento.creado_en.isoformat(),
        },
        str(uuid4()),
    )


def encolar_venta(cola: ColaSincronizacion | None, venta: Venta, turno_uuid: str) -> None:
    if cola is None:
        return
    cola.encolar(
        "venta",
        "insert",
        {
            "uuid": venta.uuid,
            "turno_uuid": turno_uuid,
            "estado": venta.estado.value,
            "creado_en": venta.creado_en.isoformat(),
            "detalles": [
                {
                    "codigo": d.producto_codigo,
                    "cantidad": str(d.cantidad),
                    "precio": d.precio_unitario.monto,
                    "costo": d.costo_unitario.monto if d.costo_unitario else None,
                    "descuento": d.descuento_linea.monto,
                }
                for d in venta.detalles
            ],
            "pagos": [{"medio": p.medio.value, "monto": p.monto.monto} for p in venta.pagos],
        },
        f"venta:{venta.uuid}",
    )


def encolar_catalogo(
    cola: ColaSincronizacion | None, productos: list[Producto], existencias: list[Existencia]
) -> int:
    """Encola todo el catalogo y stock actuales (carga inicial hacia Supabase).

    Es idempotente en el destino (upsert por codigo), asi que puede repetirse.
    """
    if cola is None:
        return 0
    for producto in productos:
        encolar_producto(cola, producto)
    for existencia in existencias:
        if existencia.cantidad >= Decimal(0):
            encolar_existencia(cola, existencia)
    return len(productos) + len(existencias)


def encolar_lote(cola: ColaSincronizacion | None, lote: Lote) -> None:
    """Un lote cambia de saldo (ingreso, venta), asi que cada cambio es una operacion nueva."""
    if cola is None:
        return
    cola.encolar(
        "lote",
        "upsert",
        {
            "uuid": lote.uuid,
            "codigo_producto": lote.codigo_producto,
            "fecha_vencimiento": lote.fecha_vencimiento.isoformat(),
            "saldo": str(lote.saldo),
        },
        str(uuid4()),
    )
