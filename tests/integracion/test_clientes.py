"""Credito a clientes (HU-CLI-01 a 05, HU-CAJ-03) con SQLite real. Datos ficticios."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
from pos.aplicacion.casos_uso.gestionar_clientes import GestionarClientes, RegistrarAbono
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.dominio.clientes import (
    abonos_del_ciclo,
    consumos_del_ciclo,
    saldo_anterior,
    saldo_de,
    ultimo_consumo,
)
from pos.dominio.errores import ReglaClienteInvalida, ReglaVentaInvalida
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite

HOY = date.today()


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        clientes = RepositorioClientesSQLite(con)
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        turnos = RepositorioTurnosCajaSQLite(con)
        ventas = RepositorioVentasSQLite(con)

    a = A()
    a.gestion = GestionarClientes(a.clientes)
    a.abono = RegistrarAbono(a.clientes, a.turnos)
    a.venta = RegistrarVenta(
        a.ventas, a.turnos, a.productos, a.existencias, repositorio_clientes=a.clientes
    )
    a.cerrar = CerrarTurnoCaja(a.turnos, a.ventas, repositorio_clientes=a.clientes)
    a.productos.guardar(Producto("ARR", "Arroz", Dinero(1000), categoria_id=1))
    a.existencias.guardar(Existencia("ARR", Decimal("100")))
    AbrirTurnoCaja(a.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(10000))
    return a


def _vender_a_credito(a, cliente_id, unidades, activo_pago=True):
    v = a.venta.iniciar(usuario_id=1, cliente_id=cliente_id)
    a.venta.agregar_producto(v, "ARR", unidades)
    a.venta.agregar_pago(v, Pago(MedioPago.CREDITO_CLIENTE, Dinero(1000 * unidades)))
    return a.venta.cerrar(v)


def test_crear_cliente_valida_nombre_contacto_y_duplicados(app):
    cliente = app.gestion.crear("  Cliente   A ", telefono="+56 9 0000 0001")
    assert cliente.nombre == "Cliente A" and cliente.id is not None
    with pytest.raises(ReglaClienteInvalida, match="nombre"):
        app.gestion.crear("  ", telefono="1")
    with pytest.raises(ReglaClienteInvalida, match="medio de contacto"):
        app.gestion.crear("Cliente B")
    with pytest.raises(ReglaClienteInvalida, match="Ya existe"):
        app.gestion.crear("cliente a", correo="a@ejemplo.cl")  # misma persona, otra grafia


def test_modificar_y_desactivar_conservan_el_historial(app):
    a = app.gestion.crear("Cliente A", telefono="1")
    _vender_a_credito(app, a.id, 3)
    app.gestion.modificar(a.id, "Cliente A.", telefono="2")
    app.gestion.cambiar_estado(a.id, False)
    cliente = app.clientes.obtener(a.id)
    assert cliente.nombre == "Cliente A." and cliente.telefono == "2" and not cliente.activo
    assert saldo_de(app.clientes.movimientos(a.id)) == 3000  # el historial sigue ahi


def test_vender_a_credito_carga_la_cuenta_y_el_saldo_se_calcula(app):
    a = app.gestion.crear("Cliente A", telefono="1")
    venta = _vender_a_credito(app, a.id, 3)
    movs = app.clientes.movimientos(a.id)
    assert len(movs) == 1 and movs[0].monto == 3000
    assert movs[0].detalle == f"Venta N° {venta.id} · 1 producto"
    assert movs[0].venta_uuid == venta.uuid
    assert saldo_de(movs) == 3000 and ultimo_consumo(movs) == HOY


def test_credito_exige_cliente_activo(app):
    a = app.gestion.crear("Cliente A", telefono="1")
    v = app.venta.iniciar(usuario_id=1)  # sin cliente
    app.venta.agregar_producto(v, "ARR", 2)
    app.venta.agregar_pago(v, Pago(MedioPago.CREDITO_CLIENTE, Dinero(2000)))
    with pytest.raises(ReglaVentaInvalida, match="Elige el cliente"):
        app.venta.cerrar(v)
    v.cliente_id = a.id
    app.gestion.cambiar_estado(a.id, False)
    with pytest.raises(ReglaVentaInvalida, match="inactivo"):
        app.venta.cerrar(v)
    assert app.existencias.obtener("ARR").cantidad == 100  # no se descontó nada
    assert app.clientes.movimientos(a.id) == []


def test_abono_baja_el_saldo_y_no_puede_superarlo(app):
    a = app.gestion.crear("Cliente A", telefono="1")
    _vender_a_credito(app, a.id, 5)
    app.abono.ejecutar(a.id, 2000, "transferencia")
    assert saldo_de(app.clientes.movimientos(a.id)) == 3000
    with pytest.raises(ReglaClienteInvalida, match="supera el saldo"):
        app.abono.ejecutar(a.id, 3001, "transferencia")
    with pytest.raises(ReglaClienteInvalida, match="medio de pago"):
        app.abono.ejecutar(a.id, 100, "cheque")
    with pytest.raises(ReglaClienteInvalida, match="mayor que cero"):
        app.abono.ejecutar(a.id, 0, "transferencia")


def test_abono_en_efectivo_entra_al_arqueo_como_partida_aparte(app):
    a = app.gestion.crear("Cliente A", telefono="1")
    _vender_a_credito(app, a.id, 5)
    app.abono.ejecutar(a.id, 2000, "efectivo")
    app.abono.ejecutar(a.id, 1000, "transferencia")  # no entra a la gaveta
    arqueo = app.cerrar.ejecutar(Dinero(12000))
    assert arqueo.abonos_efectivo.monto == 2000
    assert arqueo.efectivo_esperado == 12000  # fondo 10.000 + abono en efectivo 2.000
    assert arqueo.diferencia == 0
    assert arqueo.totales_por_medio[MedioPago.CREDITO_CLIENTE].monto == 5000  # credito aparte


def test_abono_en_efectivo_sin_jornada_abierta_se_rechaza(app):
    a = app.gestion.crear("Cliente A", telefono="1")
    _vender_a_credito(app, a.id, 5)
    app.cerrar.ejecutar(Dinero(10000))
    with pytest.raises(ReglaClienteInvalida, match="Abre la jornada"):
        app.abono.ejecutar(a.id, 1000, "efectivo")
    app.abono.ejecutar(a.id, 1000, "transferencia")  # otros medios no necesitan jornada


def test_ciclo_mensual_saldo_anterior_consumos_y_abonos(app):
    from pos.dominio.clientes import MovimientoCliente, TipoMovimientoCliente

    a = app.gestion.crear("Cliente A", telefono="1")
    mes_pasado = (HOY.replace(day=1) - timedelta(days=1)).replace(day=10)
    for tipo, monto, fecha in (
        (TipoMovimientoCliente.CONSUMO, 12400, mes_pasado),
        (TipoMovimientoCliente.CONSUMO, 18640, HOY),
        (TipoMovimientoCliente.ABONO, 5000, HOY),
    ):
        app.clientes.agregar_movimiento(MovimientoCliente(a.id, tipo, monto, fecha))
    movs = app.clientes.movimientos(a.id)
    assert saldo_anterior(movs, HOY.year, HOY.month) == 12400
    assert consumos_del_ciclo(movs, HOY.year, HOY.month) == 18640
    assert abonos_del_ciclo(movs, HOY.year, HOY.month) == 5000
    assert saldo_de(movs) == 26040
