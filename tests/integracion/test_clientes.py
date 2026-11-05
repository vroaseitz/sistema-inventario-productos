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
    descuento_credito,
    saldo_anterior,
    saldo_de,
    total_a_pagar,
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


def test_el_consumo_a_credito_lista_sus_productos_con_cantidad_y_monto(app):
    """CL-02: el estado de cuenta debe decir que se llevo, no solo «Venta N 1 · 1 producto»."""
    app.productos.guardar(Producto("MIE", "Miel de ulmo 500 g", Dinero(4990), categoria_id=1))
    app.existencias.guardar(Existencia("MIE", Decimal("10")))
    cliente = app.gestion.crear("Cliente A", telefono="1")
    v = app.venta.iniciar(usuario_id=1, cliente_id=cliente.id)
    app.venta.agregar_producto(v, "ARR", 3)
    app.venta.agregar_producto(v, "MIE", 2)
    v.aplicar_descuento("MIE", 990, "Cortesía")
    app.venta.agregar_pago(v, Pago(MedioPago.CREDITO_CLIENTE, v.total))
    venta = app.venta.cerrar(v)
    movimiento = app.clientes.movimientos(cliente.id)[0]
    lineas = app.clientes.lineas_de_consumo(movimiento.venta_uuid)
    assert [(ln.nombre, ln.cantidad, ln.monto) for ln in lineas] == [
        ("Arroz", Decimal("3"), 3000),
        ("Miel de ulmo 500 g", Decimal("2"), 8990),  # 2 x 4.990 - 990 de descuento
    ]
    assert sum(ln.monto for ln in lineas) == movimiento.monto == venta.total.monto
    assert app.clientes.lineas_de_consumo("no-existe") == []


def test_descuento_del_credito_familiar_es_20_por_ciento_del_ejemplo_de_la_hu():
    """HU-CLI-04 (PO, 22-09): $110.268 de consumos, $22.054 de descuento, $88.214 a pagar."""
    assert descuento_credito(110_268) == 22_054  # 22.053,6 redondea hacia arriba
    assert total_a_pagar(110_268) == 88_214
    assert descuento_credito(0) == 0 and total_a_pagar(0) == 0
    assert descuento_credito(5) == 1  # 1,0 exacto
    assert descuento_credito(2) == 0  # 0,4 -> 0
    assert descuento_credito(3) == 1  # 0,6 -> 1


def _con_consumo(app, monto, fecha=None):
    from pos.dominio.clientes import MovimientoCliente, TipoMovimientoCliente

    cliente = app.gestion.crear("Cliente A", telefono="1")
    app.clientes.agregar_movimiento(
        MovimientoCliente(cliente.id, TipoMovimientoCliente.CONSUMO, monto, fecha or HOY, "Consumo")
    )
    return cliente


def test_pagar_el_estado_de_cuenta_deja_la_deuda_en_cero_con_el_ejemplo_de_la_hu(app):
    """HU-CLI-04: $110.268 de consumos -> abono de $88.214 + descuento de $22.054 = saldo 0."""
    from pos.aplicacion.casos_uso.gestionar_clientes import PagarEstadoDeCuenta
    from pos.dominio.clientes import MEDIO_DESCUENTO

    cliente = _con_consumo(app, 110_268)
    pagar = PagarEstadoDeCuenta(app.clientes)
    assert pagar.calcular(cliente.id, HOY.year, HOY.month) == (88_214, 22_054)
    pago, descuento = pagar.ejecutar(cliente.id, HOY.year, HOY.month)
    assert (pago.monto, pago.medio) == (88_214, "transferencia")
    assert (descuento.monto, descuento.medio) == (22_054, MEDIO_DESCUENTO)
    movs = app.clientes.movimientos(cliente.id)
    assert saldo_de(movs) == 0
    # El descuento no es plata que entra: no cuenta como abono ni toca el efectivo de la caja.
    assert abonos_del_ciclo(movs, HOY.year, HOY.month) == 88_214
    assert app.clientes.abonos_en_efectivo_del_turno(1) == 0


def test_el_descuento_del_ciclo_se_aplica_una_sola_vez(app):
    from pos.aplicacion.casos_uso.gestionar_clientes import PagarEstadoDeCuenta

    cliente = _con_consumo(app, 50_000)
    pagar = PagarEstadoDeCuenta(app.clientes)
    pagar.ejecutar(cliente.id, HOY.year, HOY.month)
    with pytest.raises(ReglaClienteInvalida, match="ya se aplicó"):
        pagar.ejecutar(cliente.id, HOY.year, HOY.month)
    assert saldo_de(app.clientes.movimientos(cliente.id)) == 0  # sin movimientos de mas


def test_si_ya_habia_abonado_algo_solo_paga_lo_que_falta(app):
    from pos.aplicacion.casos_uso.gestionar_clientes import PagarEstadoDeCuenta

    cliente = _con_consumo(app, 100_000)
    app.abono.ejecutar(cliente.id, 30_000, "transferencia")
    pagar = PagarEstadoDeCuenta(app.clientes)
    # total a pagar = 100.000 - 20.000 = 80.000; ya abono 30.000 -> faltan 50.000
    assert pagar.calcular(cliente.id, HOY.year, HOY.month) == (50_000, 20_000)
    pagar.ejecutar(cliente.id, HOY.year, HOY.month)
    assert saldo_de(app.clientes.movimientos(cliente.id)) == 0


def test_sin_consumos_en_el_ciclo_no_hay_nada_que_pagar(app):
    from pos.aplicacion.casos_uso.gestionar_clientes import PagarEstadoDeCuenta

    cliente = app.gestion.crear("Cliente B", telefono="2")
    with pytest.raises(ReglaClienteInvalida, match="no tiene consumos"):
        PagarEstadoDeCuenta(app.clientes).ejecutar(cliente.id, HOY.year, HOY.month)
