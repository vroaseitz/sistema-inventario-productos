"""HU-REP-03 rentabilidad, HU-REP-04 rotacion y HU-PRD-06 desactivar (SQLite real)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.cambiar_estado_producto import CambiarEstadoProducto
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.casos_uso.reporte_rentabilidad import ReporteRentabilidad, ReporteRotacion
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
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
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        turnos = RepositorioTurnosCajaSQLite(con)
        ventas = RepositorioVentasSQLite(con)
        cola = ColaSincronizacionSQLite(con)
        auditoria = RepositorioAuditoriaSQLite(con)
        conexion = con

    a = A()
    a.registrar = RegistrarVenta(a.ventas, a.turnos, a.productos, a.existencias)
    a.rentabilidad = ReporteRentabilidad(a.ventas, a.productos)
    a.rotacion = ReporteRotacion(a.ventas, a.productos, a.existencias)
    costo = lambda n: Costo(neto=Dinero(n), iva=Dinero(0))  # noqa: E731
    a.productos.guardar(Producto("CAS", "Castana", Dinero(1000), categoria_id=1, costo=costo(600)))
    a.productos.guardar(
        Producto("ALM", "Almendra", Dinero(2000), categoria_id=2, costo=costo(1500))
    )
    a.productos.guardar(Producto("CRE", "Crema de mani", Dinero(4000), categoria_id=1))  # sin costo
    a.productos.guardar(
        Producto(
            "QUI", "Quinoa", Dinero(10000), UnidadVenta.GRANEL, categoria_id=2, costo=costo(6000)
        )
    )
    for codigo in ("CAS", "ALM", "CRE", "QUI"):
        a.existencias.guardar(Existencia(codigo, Decimal("100")))
    AbrirTurnoCaja(a.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    return a


def _vender(a, lineas):
    v = a.registrar.iniciar(usuario_id=1)
    for codigo, cantidad in lineas:
        a.registrar.agregar_producto(v, codigo, Decimal(str(cantidad)))
    a.registrar.agregar_pago(v, Pago(MedioPago.TARJETA, Dinero(v.total.monto)))
    return a.registrar.cerrar(v)


def _fechar(a, venta, dias_atras):
    """Mueve la venta al pasado (la prueba de rotacion necesita ventas viejas)."""
    fecha = datetime.now() - timedelta(days=dias_atras)
    a.conexion.execute(
        "UPDATE ventas SET creado_en = ? WHERE id = ?", (fecha.isoformat(), venta.id)
    )


def test_rentabilidad_calcula_ganancia_y_margen_sobre_costo_neto(app):
    _vender(app, [("CAS", 10), ("ALM", 4)])
    resumen = app.rentabilidad.ejecutar(HOY, HOY)
    por_codigo = {f.codigo: f for f in resumen.filas}
    cas, alm = por_codigo["CAS"], por_codigo["ALM"]
    assert (cas.venta, cas.costo, cas.ganancia) == (10000, 6000, 4000)
    assert cas.margen == pytest.approx(0.4)
    assert (alm.venta, alm.costo, alm.ganancia) == (8000, 6000, 2000)
    assert resumen.ganancia_total == 6000 and resumen.venta_con_costo == 18000
    assert resumen.margen_total == pytest.approx(6000 / 18000)
    assert [f.codigo for f in resumen.filas] == ["CAS", "ALM"]  # mayor ganancia primero


def test_un_producto_sin_costo_se_informa_y_no_infla_la_ganancia(app):
    _vender(app, [("CAS", 1), ("CRE", 5)])
    resumen = app.rentabilidad.ejecutar(HOY, HOY)
    crema = next(f for f in resumen.filas if f.codigo == "CRE")
    assert crema.sin_costo and crema.ganancia is None and crema.margen is None
    assert crema.venta == 20000
    assert resumen.venta_sin_costo == 20000
    assert resumen.venta_con_costo == 1000 and resumen.ganancia_total == 400  # solo la castana
    assert resumen.filas[-1].codigo == "CRE"  # los sin costo van al final al ordenar por ganancia


def test_costo_cero_cuenta_como_sin_costo(app):
    app.productos.guardar(
        Producto("CER", "Cero", Dinero(1000), categoria_id=1, costo=Costo(Dinero(0), Dinero(0)))
    )
    app.existencias.guardar(Existencia("CER", Decimal("5")))
    _vender(app, [("CER", 2)])
    fila = app.rentabilidad.ejecutar(HOY, HOY).filas[0]
    assert fila.sin_costo and fila.margen is None  # no declara 100 % de ganancia


def test_la_rentabilidad_usa_el_costo_de_cuando_se_vendio(app):
    _vender(app, [("CAS", 10)])
    app.productos.guardar(  # el costo sube despues de la venta
        Producto(
            "CAS", "Castana", Dinero(1000), categoria_id=1, costo=Costo(Dinero(900), Dinero(0))
        )
    )
    fila = next(f for f in app.rentabilidad.ejecutar(HOY, HOY).filas if f.codigo == "CAS")
    assert fila.costo == 6000 and fila.ganancia == 4000  # sigue el de la venta, no el de hoy


def test_granel_no_muestra_unidades_y_se_filtra_por_categoria_y_orden(app):
    _vender(app, [("QUI", "0.5"), ("CAS", 2), ("ALM", 1)])
    todas = app.rentabilidad.ejecutar(HOY, HOY)
    quinoa = next(f for f in todas.filas if f.codigo == "QUI")
    assert quinoa.unidades is None and quinoa.venta == 5000 and quinoa.ganancia == 2000
    solo_cat2 = app.rentabilidad.ejecutar(HOY, HOY, categoria_id=2)
    assert {f.codigo for f in solo_cat2.filas} == {"QUI", "ALM"}
    por_nombre = app.rentabilidad.ejecutar(HOY, HOY, orden="Nombre")
    assert [f.nombre for f in por_nombre.filas] == sorted(f.nombre for f in por_nombre.filas)
    with pytest.raises(ValueError):
        app.rentabilidad.ejecutar(HOY, HOY - timedelta(days=1))


def test_las_ventas_fuera_del_periodo_no_cuentan(app):
    v = _vender(app, [("CAS", 10)])
    _fechar(app, v, 40)
    assert app.rentabilidad.ejecutar(HOY - timedelta(days=7), HOY).filas == []


def test_rotacion_lista_los_productos_sin_venta_del_mas_antiguo_al_mas_reciente(app):
    _fechar(app, _vender(app, [("CAS", 1)]), 200)  # hace 200 dias
    _fechar(app, _vender(app, [("ALM", 1)]), 120)  # hace 120 dias
    _vender(app, [("CRE", 1)])  # hoy
    filas = app.rotacion.ejecutar(dias=90)
    assert [f.codigo for f in filas] == ["QUI", "CAS", "ALM"]  # QUI nunca se vendio: primero
    assert filas[0].dias_detenido is None and filas[0].ultima_venta is None
    assert filas[1].dias_detenido == 200 and filas[2].dias_detenido == 120
    assert filas[1].existencia == Decimal("99")
    assert [f.codigo for f in app.rotacion.ejecutar(dias=180)] == ["QUI", "CAS"]  # ALM ya no
    assert [f.codigo for f in app.rotacion.ejecutar(dias=90, categoria_id=1)] == ["CAS"]


def test_desactivar_saca_el_producto_de_la_venta_sin_borrar_su_historial(app):
    auditor = Auditor(app.auditoria, lambda: "roxana")
    caso = CambiarEstadoProducto(app.productos, app.cola, auditor=auditor)
    _vender(app, [("CAS", 1)])
    caso.ejecutar("CAS", False)
    assert app.productos.obtener_por_codigo("CAS").activo is False
    v = app.registrar.iniciar(usuario_id=1)
    with pytest.raises(DatosProductoInvalidos, match="desactivado"):
        app.registrar.agregar_producto(v, "CAS", 1)
    assert [f.codigo for f in app.rentabilidad.ejecutar(HOY, HOY).filas] == ["CAS"]  # historial
    assert "CAS" not in {f.codigo for f in app.rotacion.ejecutar(estado="Activos", dias=0)}
    assert "CAS" in {f.codigo for f in app.rotacion.ejecutar(estado="Inactivos", dias=0)}
    registro = app.auditoria.listar()[0]
    assert (registro["accion"], registro["antes"], registro["despues"]) == (
        "Desactivación de producto",
        "Activo",
        "Inactivo",
    )
    assert any(
        o["entidad"] == "producto" and o["datos"]["activo"] is False for o in app.cola.pendientes()
    )
    caso.ejecutar("CAS", True)
    app.registrar.agregar_producto(v, "CAS", 1)  # reactivado: vuelve a vender
    with pytest.raises(DatosProductoInvalidos, match="No existe"):
        caso.ejecutar("NOEXISTE", False)
