"""Ingreso de stock con lote, alertas de vencimiento y consumo FEFO (SQLite real)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.dominio.errores import DatosProductoInvalidos, ReglaInventarioInvalida
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite

HOY = date.today()


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        lotes = RepositorioLotesSQLite(con)
        turnos = RepositorioTurnosCajaSQLite(con)
        ventas = RepositorioVentasSQLite(con)
        cola = ColaSincronizacionSQLite(con)

    a = A()
    a.ingresar = IngresarStock(a.productos, a.existencias, a.lotes, cola=a.cola)
    a.alertas = ConsultarAlertasVencimiento(a.lotes, a.productos)
    a.venta = RegistrarVenta(
        a.ventas, a.turnos, a.productos, a.existencias, cola=a.cola, repositorio_lotes=a.lotes
    )
    a.productos.guardar(
        Producto("YOG", "Yogurt", Dinero(2000), categoria_id=1, perecible=True, dias_aviso=7)
    )
    a.productos.guardar(Producto("ARR", "Arroz", Dinero(1000), categoria_id=1))
    return a


def test_ingresar_stock_de_un_producto_nuevo_lo_deja_vendible(app):
    # C-12: lo creado en Catalogo no se podia vender por falta de stock
    app.ingresar.ejecutar("ARR", 20, "Compra proveedor")
    assert app.existencias.obtener("ARR").cantidad == Decimal("20")
    assert app.lotes.por_producto("ARR") == []  # no perecible: sin lote


def test_producto_perecible_exige_vencimiento(app):
    with pytest.raises(ReglaInventarioInvalida):
        app.ingresar.ejecutar("YOG", 10, "Compra proveedor")
    assert app.existencias.obtener("YOG") is None  # no quedo nada a medias


def test_no_se_ingresa_un_lote_ya_vencido(app):
    with pytest.raises(ReglaInventarioInvalida):
        app.ingresar.ejecutar("YOG", 10, "Compra", fecha_vencimiento=HOY - timedelta(days=1))


def test_ingresar_exige_motivo_y_producto_existente(app):
    with pytest.raises(ReglaInventarioInvalida):
        app.ingresar.ejecutar("ARR", 5, "  ")
    with pytest.raises(DatosProductoInvalidos):
        app.ingresar.ejecutar("NOPE", 5, "Compra")


def test_el_lote_se_guarda_y_se_encola_para_sincronizar(app):
    lote = app.ingresar.ejecutar("YOG", 10, "Compra", fecha_vencimiento=HOY + timedelta(days=4))
    assert app.lotes.por_producto("YOG")[0].uuid == lote.uuid
    entidades = [op["entidad"] for op in app.cola.pendientes()]
    assert "lote" in entidades and "existencia" in entidades


def test_alerta_ordena_por_urgencia_y_sugiere_descuento(app):
    app.ingresar.ejecutar("YOG", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=6))
    app.ingresar.ejecutar("YOG", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=2))
    app.ingresar.ejecutar("YOG", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=60))
    alertas = app.alertas.ejecutar(HOY)
    assert [a.dias_restantes for a in alertas] == [2, 6]  # el de 60 dias no alerta
    assert [a.descuento_pct for a in alertas] == [30, 20]
    assert alertas[0].precio_sugerido == Dinero(1400)


def test_lote_sin_saldo_no_alerta(app):
    app.ingresar.ejecutar("YOG", 3, "Compra", fecha_vencimiento=HOY + timedelta(days=1))
    app.abrir = AbrirTurnoCaja(app.turnos)
    app.abrir.ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    venta = app.venta.iniciar(usuario_id=1)
    app.venta.agregar_producto(venta, "YOG", 3)
    app.venta.agregar_pago(venta, Pago(medio=MedioPago.TARJETA, monto=Dinero(6000)))
    app.venta.cerrar(venta)
    assert app.alertas.ejecutar(HOY) == []


def test_la_venta_consume_primero_el_lote_que_vence_antes(app):
    app.ingresar.ejecutar("YOG", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=30))
    app.ingresar.ejecutar("YOG", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=3))
    AbrirTurnoCaja(app.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    venta = app.venta.iniciar(usuario_id=1)
    app.venta.agregar_producto(venta, "YOG", 7)
    app.venta.agregar_pago(venta, Pago(medio=MedioPago.TARJETA, monto=Dinero(14000)))
    app.venta.cerrar(venta)

    saldos = {lote.fecha_vencimiento: lote.saldo for lote in app.lotes.por_producto("YOG")}
    assert saldos[HOY + timedelta(days=3)] == 0  # el que vence antes se agoto
    assert saldos[HOY + timedelta(days=30)] == Decimal("3")
    assert app.existencias.obtener("YOG").cantidad == Decimal("3")  # coherente con los lotes


def test_producto_con_aviso_corto_no_alerta_un_lote_lejano(app):
    # QA 29-10: un cafe con "Dias aviso: 1" no deberia aparecer con 8 dias para vencer.
    app.productos.guardar(
        Producto("CAF", "Cafe", Dinero(3000), categoria_id=1, perecible=True, dias_aviso=1)
    )
    app.ingresar.ejecutar("CAF", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=8))
    assert app.alertas.ejecutar(HOY) == []
    app.ingresar.ejecutar("CAF", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=1))
    assert [a.dias_restantes for a in app.alertas.ejecutar(HOY)] == [1]  # solo el que vence ya


def test_el_lote_guarda_el_codigo_impreso_en_el_envase(app):
    """I-02: se escribe «L. 26089 A» al ingresar y es lo que se muestra, no «L1»."""
    con_codigo = app.ingresar.ejecutar(
        "YOG", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=20), codigo_lote=" L. 26089 A "
    )
    sin_codigo = app.ingresar.ejecutar(
        "YOG", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=30)
    )
    guardados = {x.uuid: x for x in app.lotes.por_producto("YOG")}
    assert guardados[con_codigo.uuid].codigo_lote == "L. 26089 A"
    assert guardados[con_codigo.uuid].etiqueta == "L. 26089 A"
    assert guardados[sin_codigo.uuid].etiqueta == f"L{sin_codigo.id}"  # sin codigo: numero interno


def test_una_base_con_lotes_anteriores_recibe_la_columna_del_codigo():
    con = crear_conexion(":memory:")
    con.executescript(
        "CREATE TABLE lotes (id INTEGER PRIMARY KEY AUTOINCREMENT, uuid TEXT NOT NULL UNIQUE, "
        "codigo_producto TEXT NOT NULL, fecha_vencimiento TEXT NOT NULL, saldo TEXT NOT NULL);"
        "INSERT INTO lotes (uuid, codigo_producto, fecha_vencimiento, saldo) "
        "VALUES ('u1', 'YOG', '2030-01-01', '3');"
    )
    crear_esquema(con)
    lote = RepositorioLotesSQLite(con).por_producto("YOG")[0]
    assert lote.codigo_lote == "" and lote.etiqueta == "L1"


def test_merma_da_de_baja_stock_y_lotes_y_deja_registro(app):
    """HU-INV-04: motivo obligatorio, descuenta del lote que vence antes y no se edita."""
    from pos.aplicacion.casos_uso.registrar_merma import RegistrarMerma
    from pos.dominio.inventario import MotivoAjuste
    from pos.infraestructura.sqlite.repositorio_existencias import RepositorioAjustesSQLite

    ajustes = RepositorioAjustesSQLite(app.productos._con)
    pronto = app.ingresar.ejecutar("YOG", 6, "Compra", fecha_vencimiento=HOY + timedelta(days=2))
    app.ingresar.ejecutar("YOG", 4, "Compra", fecha_vencimiento=HOY + timedelta(days=20))
    merma = RegistrarMerma(app.existencias, ajustes, app.lotes, cola=app.cola)

    ajuste = merma.ejecutar(
        "YOG", "3,5".replace(",", "."), MotivoAjuste.VENCIMIENTO, "ana", " retirado "
    )
    assert ajuste.cantidad_anterior == 10 and ajuste.cantidad_nueva == Decimal("6.5")
    assert app.existencias.obtener("YOG").cantidad == Decimal("6.5")
    saldos = {x.uuid: x.saldo for x in app.lotes.por_producto("YOG")}
    assert saldos[pronto.uuid] == Decimal("2.5")  # salio del lote que vence antes
    fila = app.productos._con.execute(
        "SELECT motivo, observacion, usuario FROM historial_ajustes_inventario"
    ).fetchone()
    assert (fila["motivo"], fila["observacion"], fila["usuario"]) == (
        "vencimiento",
        "retirado",
        "ana",
    )


def test_merma_rechaza_cantidades_invalidas_sin_tocar_el_stock(app):
    from pos.aplicacion.casos_uso.registrar_merma import RegistrarMerma
    from pos.dominio.inventario import MotivoAjuste
    from pos.infraestructura.sqlite.repositorio_existencias import RepositorioAjustesSQLite

    app.ingresar.ejecutar("ARR", 5, "Compra")
    merma = RegistrarMerma(app.existencias, RepositorioAjustesSQLite(app.productos._con), app.lotes)
    for cantidad in ("0", "-1", "abc", "6"):
        with pytest.raises(ReglaInventarioInvalida):
            merma.ejecutar("ARR", cantidad, MotivoAjuste.ROTURA, "ana")
    assert app.existencias.obtener("ARR").cantidad == 5
