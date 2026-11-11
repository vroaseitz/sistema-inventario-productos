"""HU-VTA-11: anular una venta cobrada, con motivo, sin borrarla (SQLite real, datos ficticios)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.anular_venta import AnularVenta
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
from pos.aplicacion.casos_uso.gestionar_clientes import GestionarClientes
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.registro_movimientos import RegistroMovimientos
from pos.dominio.caja import calcular_arqueo
from pos.dominio.clientes import (
    abonos_del_ciclo,
    consumos_del_ciclo,
    saldo_de,
    total_a_pagar,
)
from pos.dominio.errores import ReglaVentaInvalida
from pos.dominio.inventario import Existencia, TipoMovimiento
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import EstadoVenta
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_movimientos import RepositorioMovimientosSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite

HOY = date.today()


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        conexion = con
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        lotes = RepositorioLotesSQLite(con)
        turnos = RepositorioTurnosCajaSQLite(con)
        ventas = RepositorioVentasSQLite(con)
        clientes = RepositorioClientesSQLite(con)
        auditoria = RepositorioAuditoriaSQLite(con)
        repo_movimientos = RepositorioMovimientosSQLite(con)
        cola = ColaSincronizacionSQLite(con)

    a = A()
    a.venta = RegistrarVenta(
        a.ventas,
        a.turnos,
        a.productos,
        a.existencias,
        cola=a.cola,
        repositorio_lotes=a.lotes,
        repositorio_clientes=a.clientes,
    )
    a.anular = AnularVenta(
        a.ventas,
        a.turnos,
        a.existencias,
        cola=a.cola,
        repositorio_lotes=a.lotes,
        repositorio_clientes=a.clientes,
        movimientos=RegistroMovimientos(a.repo_movimientos, lambda: "Admin"),
        auditor=Auditor(a.auditoria, lambda: "Admin", cola=a.cola),
    )
    a.gestion = GestionarClientes(a.clientes)
    a.productos.guardar(Producto("ARR", "Arroz", Dinero(1000), categoria_id=1))
    a.productos.guardar(
        Producto("YOG", "Yogur", Dinero(2000), categoria_id=1, perecible=True, dias_aviso=30)
    )
    a.existencias.guardar(Existencia("ARR", Decimal("50")))
    ingreso = IngresarStock(a.productos, a.existencias, a.lotes)
    ingreso.ejecutar(
        "YOG", 4, "Compra", fecha_vencimiento=HOY + timedelta(days=5)
    )  # L1: vence antes
    ingreso.ejecutar("YOG", 4, "Compra", fecha_vencimiento=HOY + timedelta(days=40))  # L2
    AbrirTurnoCaja(a.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(10000))
    return a


def _vender(a, lineas, medio=MedioPago.EFECTIVO, cliente_id=None, elegido=None):
    v = a.venta.iniciar(usuario_id=1, cliente_id=cliente_id)
    for codigo, cantidad in lineas:
        a.venta.agregar_producto(v, codigo, cantidad)
    if elegido:
        a.venta.elegir_lote(v, *elegido)
    a.venta.agregar_pago(v, Pago(medio, Dinero(v.total.monto)))
    return a.venta.cerrar(v)


def _saldos_de_yogur(a):
    return [x.saldo for x in a.lotes.por_producto("YOG")]


def test_anular_conserva_la_venta_con_motivo_autor_y_fecha(app):
    v = _vender(app, [("ARR", 3)])
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    guardada = app.ventas.obtener(v.id)
    assert guardada is not None  # la venta anulada no se elimina
    assert guardada.estado is EstadoVenta.ANULADA
    assert guardada.motivo_anulacion == "Producto en mal estado"
    assert guardada.anulada_por == "Admin" and guardada.anulada_en is not None
    assert len(guardada.detalles) == 1 and len(guardada.pagos) == 1  # sigue completa


def test_el_motivo_es_de_la_lista_y_otro_se_escribe(app):
    v = _vender(app, [("ARR", 1)])
    with pytest.raises(ReglaVentaInvalida, match="motivo de la lista"):
        app.anular.ejecutar(v.id, "Porque sí", "", "Admin")
    with pytest.raises(ReglaVentaInvalida, match="escribe cuál"):
        app.anular.ejecutar(v.id, "Otro", "   ", "Admin")
    assert app.ventas.obtener(v.id).estado is EstadoVenta.PAGADA  # nada cambio
    app.anular.ejecutar(v.id, "Otro", "Cobro equivocado", "Admin")
    assert app.ventas.obtener(v.id).motivo_anulacion == "Otro: Cobro equivocado"


def test_la_existencia_vuelve_con_un_movimiento_de_reversa(app):
    v = _vender(app, [("ARR", 3)])
    assert app.existencias.obtener("ARR").cantidad == Decimal("47")
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    assert app.existencias.obtener("ARR").cantidad == Decimal("50")
    reversas = app.repo_movimientos.listar(tipo=TipoMovimiento.ANULACION, codigo="ARR")
    assert len(reversas) == 1 and reversas[0].cantidad == Decimal("3")  # entra, no sale


def test_la_existencia_vuelve_al_lote_del_que_salio(app):
    # se elige a mano el lote que vence despues (L2): la anulacion lo devuelve a ese, no al primero
    segundo = app.lotes.por_producto("YOG")[1]
    v = _vender(app, [("YOG", 2)], elegido=("YOG", segundo.uuid))
    assert _saldos_de_yogur(app) == [Decimal("4"), Decimal("2")]
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    assert _saldos_de_yogur(app) == [Decimal("4"), Decimal("4")]
    assert app.existencias.obtener("YOG").cantidad == Decimal("8")


def test_una_venta_dividida_en_dos_lotes_los_restituye_a_cada_uno(app):
    v = _vender(app, [("YOG", 6)])  # FEFO: 4 de L1 y 2 de L2
    assert _saldos_de_yogur(app) == [Decimal("0"), Decimal("2")]
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    assert _saldos_de_yogur(app) == [Decimal("4"), Decimal("4")]


def test_una_venta_anulada_no_se_anula_de_nuevo(app):
    v = _vender(app, [("ARR", 1)])
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    with pytest.raises(ReglaVentaInvalida, match="ya está anulada"):
        app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    assert app.existencias.obtener("ARR").cantidad == Decimal("50")  # no se repuso dos veces


def test_si_se_pago_a_credito_el_consumo_se_revierte_en_la_cuenta(app):
    c = app.gestion.crear("Cliente A", telefono="1", cupo=10000)
    v = _vender(app, [("ARR", 4)], MedioPago.CREDITO_CLIENTE, cliente_id=c.id)
    assert saldo_de(app.clientes.movimientos(c.id)) == 4000
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    movs = app.clientes.movimientos(c.id)
    assert saldo_de(movs) == 0  # el consumo se revirtio
    assert len(movs) == 2  # no se borro nada: queda el consumo y su reversa
    # la reversa no es un pago del cliente y no cuenta como consumo del ciclo ni para el 20 %
    assert abonos_del_ciclo(movs, HOY.year, HOY.month) == 0
    consumos = consumos_del_ciclo(movs, HOY.year, HOY.month)
    assert consumos == 0 and total_a_pagar(consumos) == 0


def test_la_anulacion_libera_el_cupo(app):
    c = app.gestion.crear("Cliente A", telefono="1", cupo=4000)
    v = _vender(app, [("ARR", 4)], MedioPago.CREDITO_CLIENTE, cliente_id=c.id)
    with pytest.raises(ReglaVentaInvalida, match="cupo"):
        _vender(app, [("ARR", 1)], MedioPago.CREDITO_CLIENTE, cliente_id=c.id)
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    _vender(app, [("ARR", 4)], MedioPago.CREDITO_CLIENTE, cliente_id=c.id)  # vuelve a comprar


def test_el_cierre_la_cuenta_como_partida_propia_y_el_efectivo_cuadra(app):
    a1 = _vender(app, [("ARR", 2)])  # $2.000 en efectivo, queda
    a2 = _vender(app, [("ARR", 3)])  # $3.000 en efectivo, se anula
    app.anular.ejecutar(a2.id, "Producto en mal estado", "", "Admin")
    turno = app.turnos.obtener_abierto()
    arqueo = calcular_arqueo(turno, app.ventas.obtener_por_turno(turno.id), Dinero(0))
    assert arqueo.totales_por_medio[MedioPago.EFECTIVO].monto == 2000  # solo lo que quedo
    assert arqueo.efectivo_esperado == 10000 + 2000  # lo anulado se devolvio al cliente
    assert arqueo.ventas_anuladas == 1 and arqueo.monto_anulado.monto == 3000  # partida propia
    assert a1.estado is EstadoVenta.PAGADA


def test_solo_se_anulan_ventas_de_la_jornada_abierta(app):
    v = _vender(app, [("ARR", 1)])
    CerrarTurnoCaja(app.turnos, app.ventas).ejecutar(Dinero(11000))
    AbrirTurnoCaja(app.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(5000))
    with pytest.raises(ReglaVentaInvalida, match="jornada abierta"):
        app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    with pytest.raises(ReglaVentaInvalida, match="no existe"):
        app.anular.ejecutar(999, "Producto en mal estado", "", "Admin")


def test_queda_en_la_auditoria_con_usuario_y_motivo_y_se_encola_para_sincronizar(app):
    v = _vender(app, [("ARR", 1)])
    app.anular.ejecutar(v.id, "Otro", "Cobro equivocado", "Admin")
    fila = app.auditoria.listar(accion="Anulación de venta")[0]
    assert fila["usuario"] == "Admin" and f"Venta N° {v.id}" in fila["registro"]
    assert fila["antes"] == "pagada" and "Cobro equivocado" in fila["despues"]
    pendientes = [p for p in app.cola.pendientes() if p["entidad"] == "venta_anular"]
    assert len(pendientes) == 1
    assert pendientes[0]["datos"]["uuid"] == v.uuid
    assert pendientes[0]["datos"]["motivo"] == "Otro: Cobro equivocado"


def test_una_venta_anulada_no_cuenta_en_los_reportes(app):
    v = _vender(app, [("ARR", 2)])
    desde = hasta = HOY
    assert len(app.ventas.por_periodo(desde, hasta)) == 1
    app.anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    assert app.ventas.por_periodo(desde, hasta) == []
    assert app.ventas.ultima() is None  # tampoco se reimprime como ultima venta
