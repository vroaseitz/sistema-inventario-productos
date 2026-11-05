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
from pos.dominio.clientes import Cliente, MovimientoCliente
from pos.dominio.compras import FacturaCompra
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
            "costo": producto.costo.neto.monto if producto.costo is not None else None,
            "perecible": producto.perecible,
            "dias_aviso": producto.dias_aviso,
            "stock_minimo": producto.stock_minimo,
            # Nombre (no id local): el id de la categoria cambia entre la base local y la remota.
            "categoria": categoria,
        },
        str(uuid4()),
    )


def encolar_producto_codigo(cola: ColaSincronizacion | None, anterior: str, nuevo: str) -> None:
    """El producto cambia de codigo de barras (CA-19): el destino lo renombra, no crea otro."""
    if cola is None:
        return
    cola.encolar("producto_codigo", "update", {"anterior": anterior, "nuevo": nuevo}, str(uuid4()))


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
            "nota": venta.nota,
            "detalles": [
                {
                    "codigo": d.producto_codigo,
                    "cantidad": str(d.cantidad),
                    "precio": d.precio_unitario.monto,
                    "costo": d.costo_unitario.monto if d.costo_unitario else None,
                    "descuento": d.descuento_linea.monto,
                    "motivo_descuento": d.motivo_descuento,
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
            "codigo_lote": lote.codigo_lote,
        },
        str(uuid4()),
    )


def encolar_categoria(cola: ColaSincronizacion | None, nombre: str, activa: bool = True) -> None:
    """Una categoria se crea, se activa o se desactiva (el destino hace upsert por nombre)."""
    if cola is None:
        return
    cola.encolar("categoria", "upsert", {"nombre": nombre, "activa": activa}, str(uuid4()))


def encolar_categoria_renombrada(
    cola: ColaSincronizacion | None, anterior: str, nuevo: str
) -> None:
    if cola is None:
        return
    cola.encolar(
        "categoria_renombrar", "update", {"anterior": anterior, "nuevo": nuevo}, str(uuid4())
    )


def encolar_categoria_eliminada(cola: ColaSincronizacion | None, nombre: str) -> None:
    """Despues de fusionar: el destino solo la borra si ya no tiene productos."""
    if cola is None:
        return
    cola.encolar("categoria_eliminar", "delete", {"nombre": nombre}, str(uuid4()))


# --- Clientes, credito, proveedores, facturas de compra y auditoria (migracion 008) ---------


def _datos_cliente(cliente: Cliente) -> dict:
    """El id local es estable (una sola caja por base), asi que sirve de clave en el destino."""
    return {
        "id": f"cliente:{cliente.id}",
        "nombre": cliente.nombre,
        "telefono": cliente.telefono,
        "correo": cliente.correo,
        "observaciones": cliente.observaciones,
        "activo": cliente.activo,
    }


def encolar_cliente(cola: ColaSincronizacion | None, cliente: Cliente) -> None:
    """Un cliente se crea, se modifica o se desactiva (el destino hace upsert por su id)."""
    if cola is None or cliente.id is None:
        return
    cola.encolar("cliente", "upsert", _datos_cliente(cliente), str(uuid4()))


def encolar_movimiento_cliente(
    cola: ColaSincronizacion | None, cliente: Cliente, movimiento: MovimientoCliente
) -> None:
    """Un consumo, un abono o el descuento del credito. Lleva al cliente: si aun no llego, entra."""
    if cola is None or cliente.id is None:
        return
    cola.encolar(
        "movimiento_cliente",
        "insert",
        {
            "uuid": movimiento.uuid,
            "cliente": _datos_cliente(cliente),
            "tipo": movimiento.tipo.value,
            "monto": movimiento.monto,
            "fecha": movimiento.fecha.isoformat(),
            "detalle": movimiento.detalle,
            "medio": movimiento.medio,
            "venta_uuid": movimiento.venta_uuid,
        },
        f"movimiento-cliente:{movimiento.uuid}",
    )


def encolar_proveedor(cola: ColaSincronizacion | None, nombre: str, contacto: str = "") -> None:
    if cola is None:
        return
    cola.encolar("proveedor", "upsert", {"nombre": nombre, "contacto": contacto}, str(uuid4()))


def encolar_factura_compra(cola: ColaSincronizacion | None, factura: FacturaCompra) -> None:
    """Una factura confirmada no se edita: se envia una vez, con el proveedor y todas sus lineas."""
    if cola is None:
        return
    cola.encolar(
        "factura_compra",
        "insert",
        {
            "proveedor": factura.proveedor,
            "numero": factura.numero,
            "fecha": factura.fecha.isoformat(),
            "neto": factura.neto,
            "impuestos": factura.impuestos,
            "estado": factura.estado.value,
            "lineas": [
                {
                    "codigo": linea.codigo_producto,
                    "cantidad": str(linea.cantidad),
                    "costo": linea.costo_unitario_neto,
                    "costo_anterior": linea.costo_anterior,
                    "vence": linea.fecha_vencimiento.isoformat()
                    if linea.fecha_vencimiento
                    else None,
                    "lote": linea.codigo_lote,
                }
                for linea in factura.lineas
            ],
        },
        f"factura:{factura.proveedor.strip().lower()}:{factura.numero.strip()}",
    )


def encolar_auditoria(
    cola: ColaSincronizacion | None,
    id_local: int | None,
    fecha: str,
    usuario: str,
    accion: str,
    registro: str,
    antes: str,
    despues: str,
    detalle: str,
) -> None:
    if cola is None or id_local is None:
        return
    cola.encolar(
        "auditoria",
        "insert",
        {
            "id": f"auditoria:{id_local}",
            "fecha": fecha,
            "usuario": usuario,
            "accion": accion,
            "registro": registro,
            "antes": antes,
            "despues": despues,
            "detalle": detalle,
        },
        f"auditoria:{id_local}",
    )
