"""HU-REP-01 / HU-REP-05: resumen del dia con venta, ganancia, meta y avisos (SQLite real)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento
from pos.aplicacion.casos_uso.consultar_inventario import ConsultarExistencias
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.casos_uso.reporte_rentabilidad import ReporteRentabilidad
from pos.aplicacion.casos_uso.resumen_del_dia import ResumenDelDia, clave_de_meta
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Costo, Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_configuracion import RepositorioConfiguracionSQLite
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
        config = RepositorioConfiguracionSQLite(con)

    a = A()
    a.venta = RegistrarVenta(a.ventas, a.turnos, a.productos, a.existencias)
    a.resumen = ResumenDelDia(
        a.ventas,
        a.productos,
        ReporteRentabilidad(a.ventas, a.productos),
        ConsultarAlertasVencimiento(a.lotes, a.productos, configuracion=a.config),
        ConsultarExistencias(a.productos, a.existencias, a.ventas),
        a.config,
    )
    costo = lambda n: Costo(neto=Dinero(n), iva=Dinero(0))  # noqa: E731
    a.productos.guardar(
        Producto("CAS", "Castana", Dinero(1000), categoria_id=1, costo=costo(600), stock_minimo=200)
    )
    a.productos.guardar(Producto("CRE", "Crema", Dinero(4000), categoria_id=1))  # sin costo
    a.productos.guardar(Producto("PAN", "Pan", Dinero(2000), categoria_id=1, costo=costo(1000)))
    for codigo in ("CAS", "CRE", "PAN"):
        a.existencias.guardar(Existencia(codigo, Decimal("100")))
    IngresarStock(a.productos, a.existencias, a.lotes).ejecutar(
        "PAN", 5, "Compra", fecha_vencimiento=HOY + timedelta(days=2)
    )
    AbrirTurnoCaja(a.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    return a


def _vender(a, lineas, medio=MedioPago.TARJETA):
    v = a.venta.iniciar(usuario_id=1)
    for codigo, cantidad in lineas:
        a.venta.agregar_producto(v, codigo, cantidad)
    a.venta.agregar_pago(v, Pago(medio, Dinero(v.total.monto)))
    return a.venta.cerrar(v)


def test_venta_ganancia_medios_y_ranking(app):
    # 10.000 + 10.000 con IVA (neto 8.403 c/u): ganancia 2.403 + 3.403
    _vender(app, [("CAS", 10), ("PAN", 5)])
    _vender(app, [("CRE", 1)], MedioPago.TRANSFERENCIA)  # 4.000 sin costo
    r = app.resumen.ejecutar()
    assert (r.venta_hoy, r.transacciones) == (24000, 2)
    assert r.ganancia_hoy == 5806 and r.margen_hoy == pytest.approx(5806 / 16806)
    assert r.por_medio[MedioPago.TARJETA] == (20000, 1)
    assert r.por_medio[MedioPago.TRANSFERENCIA] == (4000, 1)
    assert r.por_medio[MedioPago.EFECTIVO] == (0, 0)
    assert [f.codigo for f in r.mayor_ganancia] == ["PAN", "CAS"]  # la crema sin costo no entra
    assert r.venta_semana >= r.venta_hoy and r.jornadas_semana == 1


def test_las_metas_por_defecto_son_las_de_la_product_owner(app):
    assert app.config.obtener("meta_lunes_viernes") == 220_000
    assert app.config.obtener("meta_sabado") == 182_000
    assert app.config.obtener("meta_domingo") == 88_000


def test_con_la_meta_en_cero_no_se_inventa_un_cumplimiento(app):
    _vender(app, [("CAS", 10)])
    app.config.guardar(clave_de_meta(HOY), 0)
    r = app.resumen.ejecutar()
    assert r.meta == 0 and r.cumplimiento is None


def test_meta_por_tipo_de_dia_y_cumplimiento(app):
    _vender(app, [("CAS", 10)])  # vende $10.000 (la meta es sobre el monto vendido)
    app.config.guardar(clave_de_meta(HOY), 20_000)
    assert app.resumen.ejecutar().cumplimiento == pytest.approx(0.5)
    app.config.guardar(clave_de_meta(HOY), 10_000)
    assert app.resumen.ejecutar().cumplimiento == pytest.approx(1.0)
    assert clave_de_meta(date(2026, 11, 7)) == "meta_sabado"
    assert clave_de_meta(date(2026, 11, 8)) == "meta_domingo"
    assert clave_de_meta(date(2026, 11, 9)) == "meta_lunes_viernes"


def test_avisos_lotes_bajo_minimo_y_sin_costo(app):
    r = app.resumen.ejecutar()
    titulos = {a.destino: a for a in r.avisos}
    assert titulos["alertas"].titulo == "1 lote por vencer" and titulos["alertas"].urgente
    assert "Pan vence en 2 días" in titulos["alertas"].detalle
    assert titulos["existencias"].titulo == "1 producto bajo el mínimo"  # CAS: 100 < 200
    assert titulos["productos"].titulo == "1 producto sin costo cargado"  # CRE
