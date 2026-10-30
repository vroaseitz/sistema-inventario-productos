"""Reporte de ventas por periodo y categoria con SQLite real (HU-REP-02)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.casos_uso.reporte_ventas import ReporteVentas
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite


@pytest.fixture
def entorno():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    productos = RepositorioProductosSQLite(con)
    existencias = RepositorioExistenciasSQLite(con)
    productos.guardar(Producto("A", "Arroz", Dinero(1000), categoria_id=1))
    productos.guardar(Producto("B", "Jabon", Dinero(2000), categoria_id=2))
    for codigo in ("A", "B"):
        existencias.guardar(Existencia(codigo, Decimal("100")))
    turnos = RepositorioTurnosCajaSQLite(con)
    ventas = RepositorioVentasSQLite(con)
    AbrirTurnoCaja(turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    registrar = RegistrarVenta(ventas, turnos, productos, existencias)

    def vender(codigo, cantidad, total, medio=MedioPago.TARJETA):
        venta = registrar.iniciar(usuario_id=1)
        registrar.agregar_producto(venta, codigo, cantidad)
        registrar.agregar_pago(venta, Pago(medio=medio, monto=Dinero(total)))
        registrar.cerrar(venta)

    return con, ventas, ReporteVentas(ventas, productos), vender


def test_totales_por_categoria_y_medio_de_pago(entorno):
    _, _, reporte, vender = entorno
    vender("A", 3, 3000)
    vender("B", 1, 2000, MedioPago.TRANSFERENCIA)
    vender("A", 1, 1000)
    hoy = date.today()
    r = reporte.ejecutar(hoy, hoy)
    assert r.cantidad_ventas == 3 and r.total == 6000
    assert r.por_categoria == {1: 4000, 2: 2000}
    assert r.por_medio_pago == {"tarjeta": 4000, "transferencia": 2000}
    assert r.ticket_promedio == 2000


def test_el_periodo_excluye_otras_fechas(entorno):
    con, _, reporte, vender = entorno
    vender("A", 1, 1000)
    vender("A", 1, 1000)
    con.execute("UPDATE ventas SET creado_en = ? WHERE id = 1", ("2020-01-15 10:00:00",))
    hoy = date.today()
    assert reporte.ejecutar(hoy, hoy).cantidad_ventas == 1
    assert reporte.ejecutar(date(2020, 1, 1), date(2020, 1, 31)).total == 1000


def test_no_cuenta_ventas_anuladas(entorno):
    con, _, reporte, vender = entorno
    vender("A", 1, 1000)
    con.execute("UPDATE ventas SET estado = 'anulada'")
    hoy = date.today()
    assert reporte.ejecutar(hoy, hoy).cantidad_ventas == 0


def test_periodo_vacio_y_rango_invalido(entorno):
    _, _, reporte, _ = entorno
    lejano = date(2001, 1, 1)
    assert reporte.ejecutar(lejano, lejano).ticket_promedio == 0
    with pytest.raises(ValueError):
        reporte.ejecutar(date.today(), date.today() - timedelta(days=1))
