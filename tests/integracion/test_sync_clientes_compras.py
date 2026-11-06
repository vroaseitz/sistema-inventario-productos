"""Clientes, credito, proveedores, facturas y auditoria encolan su operacion (migracion 008).

SQLite real y la cola real: se comprueba que cada accion de la app encola lo que el traductor sabe
enviar a Supabase, y que el traductor lo convierte en SQL sin errores.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.gestionar_clientes import (
    GestionarClientes,
    PagarEstadoDeCuenta,
    RegistrarAbono,
)
from pos.aplicacion.casos_uso.gestionar_proveedores import GestionarProveedores
from pos.aplicacion.casos_uso.registrar_factura_compra import RegistrarFacturaCompra
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.dominio.clientes import MovimientoCliente, TipoMovimientoCliente
from pos.dominio.compras import FacturaCompra, LineaFactura, iva_de
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_facturas_compra import RepositorioFacturasCompraSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_proveedores import RepositorioProveedoresSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite
from pos.infraestructura.supabase.traductor import traducir_operacion

HOY = date.today()


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        clientes = RepositorioClientesSQLite(con)
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        lotes = RepositorioLotesSQLite(con)
        facturas = RepositorioFacturasCompraSQLite(con)
        proveedores = RepositorioProveedoresSQLite(con)
        turnos = RepositorioTurnosCajaSQLite(con)
        ventas = RepositorioVentasSQLite(con)
        auditoria = RepositorioAuditoriaSQLite(con)
        cola = ColaSincronizacionSQLite(con)

    a = A()
    a.gestion = GestionarClientes(a.clientes, cola=a.cola)
    a.abono = RegistrarAbono(a.clientes, a.turnos, cola=a.cola)
    a.pagar = PagarEstadoDeCuenta(a.clientes, cola=a.cola)
    a.venta = RegistrarVenta(
        a.ventas,
        a.turnos,
        a.productos,
        a.existencias,
        cola=a.cola,
        repositorio_clientes=a.clientes,
    )
    a.productos.guardar(Producto("ARR", "Arroz", Dinero(1000), categoria_id=1))
    a.existencias.guardar(Existencia("ARR", Decimal("100")))
    AbrirTurnoCaja(a.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(10000))
    return a


def _pendientes(app, entidad):
    return [p for p in app.cola.pendientes() if p["entidad"] == entidad]


def _se_traduce(operacion):
    """Cada operacion encolada tiene que poder convertirse en SQL (si no, bloquearia la cola)."""
    assert traducir_operacion(operacion)


def test_crear_modificar_y_desactivar_un_cliente_encola_cada_cambio(app):
    cliente = app.gestion.crear("Carolina Muñoz", telefono="+56 9 1111 1111")
    app.gestion.modificar(cliente.id, "Carolina Muñoz R.", telefono="+56 9 2222 2222")
    app.gestion.cambiar_estado(cliente.id, False)
    ops = _pendientes(app, "cliente")
    assert [o["datos"]["nombre"] for o in ops] == [
        "Carolina Muñoz",
        "Carolina Muñoz R.",
        "Carolina Muñoz R.",
    ]
    assert {o["datos"]["id"] for o in ops} == {f"cliente:{cliente.id}"}  # siempre el mismo cliente
    assert [o["datos"]["activo"] for o in ops] == [True, True, False]
    for op in ops:
        _se_traduce(op)


def test_la_venta_a_credito_encola_el_consumo_con_su_cliente_y_su_venta(app):
    cliente = app.gestion.crear("Carolina Muñoz", telefono="1")
    v = app.venta.iniciar(usuario_id=1, cliente_id=cliente.id)
    app.venta.agregar_producto(v, "ARR", 3)
    app.venta.agregar_pago(v, Pago(MedioPago.CREDITO_CLIENTE, Dinero(3000)))
    venta = app.venta.cerrar(v)
    (op,) = _pendientes(app, "movimiento_cliente")
    d = op["datos"]
    assert (d["tipo"], d["monto"], d["venta_uuid"]) == ("consumo", 3000, venta.uuid)
    assert d["cliente"]["id"] == f"cliente:{cliente.id}"
    assert op["id_cliente"] == f"movimiento-cliente:{d['uuid']}"
    _se_traduce(op)


def test_un_abono_encola_su_movimiento(app):
    cliente = app.gestion.crear("Carolina Muñoz", telefono="1")
    app.clientes.agregar_movimiento(
        MovimientoCliente(cliente.id, TipoMovimientoCliente.CONSUMO, 10000, HOY, "Consumo")
    )
    app.abono.ejecutar(cliente.id, 4000, "transferencia")
    (op,) = _pendientes(app, "movimiento_cliente")
    assert (op["datos"]["tipo"], op["datos"]["monto"], op["datos"]["medio"]) == (
        "abono",
        4000,
        "transferencia",
    )
    _se_traduce(op)


def test_pagar_el_estado_de_cuenta_encola_el_pago_y_el_descuento(app):
    cliente = app.gestion.crear("Carolina Muñoz", telefono="1")
    app.clientes.agregar_movimiento(
        MovimientoCliente(cliente.id, TipoMovimientoCliente.CONSUMO, 110_268, HOY, "Consumo")
    )
    app.pagar.ejecutar(cliente.id, HOY.year, HOY.month)
    ops = _pendientes(app, "movimiento_cliente")
    assert sorted((o["datos"]["medio"], o["datos"]["monto"]) for o in ops) == [
        ("descuento", 22_054),
        ("transferencia", 88_214),
    ]
    for op in ops:
        _se_traduce(op)


def test_crear_un_proveedor_encola_su_nombre_y_contacto(app):
    GestionarProveedores(app.proveedores, app.facturas, cola=app.cola).crear(
        "Distribuidora Sur", "ventas@sur.cl"
    )
    (op,) = _pendientes(app, "proveedor")
    assert op["datos"] == {"nombre": "Distribuidora Sur", "contacto": "ventas@sur.cl"}
    _se_traduce(op)


def test_confirmar_una_factura_encola_la_factura_con_todas_sus_lineas(app):
    app.productos.guardar(
        Producto("YOG", "Yogurt", Dinero(2490), categoria_id=1, perecible=True, dias_aviso=5)
    )
    caso = RegistrarFacturaCompra(
        app.facturas, app.productos, app.existencias, app.lotes, cola=app.cola
    )
    lineas = [
        LineaFactura("ARR", 10, 600),
        LineaFactura("YOG", 24, 1500, HOY + timedelta(days=5), "L-YOG-1"),
    ]
    neto = sum(x.subtotal for x in lineas)
    caso.confirmar(FacturaCompra("Distribuidora Sur", "F-1001", HOY, neto, iva_de(neto), lineas))
    (op,) = _pendientes(app, "factura_compra")
    d = op["datos"]
    assert (d["proveedor"], d["numero"], d["neto"], d["estado"]) == (
        "Distribuidora Sur",
        "F-1001",
        neto,
        "confirmada",
    )
    assert [(x["codigo"], x["cantidad"], x["costo"]) for x in d["lineas"]] == [
        ("ARR", "10", 600),
        ("YOG", "24", 1500),
    ]
    assert d["lineas"][1]["lote"] == "L-YOG-1" and d["lineas"][1]["vence"] is not None
    assert d["lineas"][0]["costo_anterior"] is None
    _se_traduce(op)


def test_cada_entrada_de_auditoria_encola_su_registro_con_su_id(app):
    auditor = Auditor(app.auditoria, lambda: "admin", cola=app.cola)
    auditor.registrar("Cambio de precio", "Miel (7801)", "$4.990", "$5.490", {"motivo": "alza"})
    auditor.registrar("Nueva categoría", "Té", "—", "creada")
    ops = _pendientes(app, "auditoria")
    assert [o["datos"]["accion"] for o in ops] == ["Cambio de precio", "Nueva categoría"]
    ids = [o["datos"]["id"] for o in ops]
    assert all(i.startswith("auditoria:") for i in ids) and len(set(ids)) == 2  # clave propia
    assert [o["id_cliente"] for o in ops] == ids  # y es la que evita duplicar al reintentar
    assert (
        ops[0]["datos"]["usuario"] == "admin" and '"motivo": "alza"' in ops[0]["datos"]["detalle"]
    )
    for op in ops:
        _se_traduce(op)


def test_sin_cola_todo_sigue_funcionando_igual():
    """Sin Supabase configurado no hay cola: nada se encola y nada falla."""
    con = crear_conexion(":memory:")
    crear_esquema(con)
    clientes = RepositorioClientesSQLite(con)
    GestionarClientes(clientes).crear("Carolina", telefono="1")
    Auditor(RepositorioAuditoriaSQLite(con), lambda: "admin").registrar("Accion", "x", "a", "b")
    assert ColaSincronizacionSQLite(con).pendientes() == []
