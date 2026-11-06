"""Factura de compra (HU-CMP-01/02): el detalle actualiza el costo y crea el lote (SQLite real)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.registrar_factura_compra import RegistrarFacturaCompra
from pos.dominio.compras import FacturaCompra, LineaFactura, iva_de
from pos.dominio.errores import ReglaCompraInvalida
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Costo, Dinero
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_facturas_compra import RepositorioFacturasCompraSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite

HOY = date.today()


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        lotes = RepositorioLotesSQLite(con)
        facturas = RepositorioFacturasCompraSQLite(con)
        cola = ColaSincronizacionSQLite(con)

    a = A()
    a.caso = RegistrarFacturaCompra(a.facturas, a.productos, a.existencias, a.lotes, cola=a.cola)
    a.productos.guardar(Producto("CAS", "Castana de caju", Dinero(15000), categoria_id=1))
    a.productos.guardar(
        Producto("CRE", "Crema de mani", Dinero(4000), categoria_id=1, perecible=True, dias_aviso=7)
    )
    a.productos.guardar(
        Producto(
            "ALM",
            "Almendra",
            Dinero(5000),
            categoria_id=1,
            costo=Costo(neto=Dinero(3120), iva=Dinero(0)),
        )
    )
    return a


def _factura(lineas, neto=None, numero="F-4519"):
    suma = sum(x.subtotal for x in lineas)
    neto = suma if neto is None else neto
    return FacturaCompra("Distribuidora Andes", numero, HOY, neto, iva_de(neto), lineas)


def test_confirmar_actualiza_costo_ingresa_stock_y_crea_el_lote(app):
    factura = _factura(
        [
            LineaFactura("CAS", 10, 11765),
            LineaFactura("ALM", 20, 2940),
            LineaFactura("CRE", 5, 2170, HOY + timedelta(days=30), "L. 26089 A"),
        ]
    )
    assert factura.neto == 187300 and factura.impuestos == 35587 and factura.total == 222887
    app.caso.confirmar(factura)

    assert app.productos.obtener_por_codigo("CAS").costo.neto.monto == 11765
    assert app.productos.obtener_por_codigo("CRE").costo.neto.monto == 2170  # no tenia costo
    assert app.productos.obtener_por_codigo("ALM").costo.neto.monto == 2940
    assert app.existencias.obtener("CAS").cantidad == 10
    assert app.existencias.obtener("ALM").cantidad == 20
    lote = app.lotes.por_producto("CRE")[0]
    assert lote.saldo == 5 and lote.etiqueta == "L. 26089 A"
    guardada = app.facturas.listar()[0]
    assert [x.costo_anterior for x in guardada.lineas] == [None, 3120, None]
    assert app.facturas.proveedores() == ["Distribuidora Andes"]
    # el costo nuevo y el stock quedan en la cola hacia Supabase
    entidades = [o["entidad"] for o in app.cola.pendientes()]
    assert "producto" in entidades and "existencia" in entidades and "lote" in entidades


def test_el_neto_debe_coincidir_con_el_detalle(app):
    factura = _factura([LineaFactura("CAS", 10, 11765)], neto=117000)
    with pytest.raises(ReglaCompraInvalida, match="debe ser cero"):
        app.caso.confirmar(factura)


@pytest.mark.parametrize(
    "cambio, texto",
    [
        ({"proveedor": " "}, "Falta el proveedor"),
        ({"numero": ""}, "Falta el número de documento"),
        ({"lineas": []}, "al menos una línea"),
    ],
)
def test_datos_obligatorios(app, cambio, texto):
    factura = _factura([LineaFactura("CAS", 1, 1000)])
    for campo, valor in cambio.items():
        setattr(factura, campo, valor)
    with pytest.raises(ReglaCompraInvalida, match=texto):
        app.caso.confirmar(factura)


def test_una_factura_con_un_error_no_deja_nada_a_medias(app):
    """Perecible sin vencimiento en la 2.a linea: la 1.a no debe haber cambiado costo ni stock."""
    factura = _factura([LineaFactura("CAS", 10, 11765), LineaFactura("CRE", 5, 2170)])
    with pytest.raises(ReglaCompraInvalida, match="perecible"):
        app.caso.confirmar(factura)
    assert app.productos.obtener_por_codigo("CAS").costo is None
    assert app.existencias.obtener("CAS") is None
    assert app.facturas.listar() == []


def test_no_se_repite_la_misma_factura_del_mismo_proveedor(app):
    app.caso.confirmar(_factura([LineaFactura("CAS", 1, 1000)]))
    with pytest.raises(ReglaCompraInvalida, match="Ya existe"):
        app.caso.confirmar(_factura([LineaFactura("CAS", 1, 1000)]))
    assert len(app.facturas.listar()) == 1


def test_lote_vencido_o_producto_inexistente_se_rechazan(app):
    with pytest.raises(ReglaCompraInvalida, match="vencido"):
        app.caso.confirmar(_factura([LineaFactura("CRE", 1, 1000, HOY - timedelta(days=1))]))
    with pytest.raises(ReglaCompraInvalida, match="No existe el producto"):
        app.caso.confirmar(_factura([LineaFactura("XXX", 1, 1000)]))


def test_lineas_invalidas():
    with pytest.raises(ReglaCompraInvalida):
        LineaFactura("CAS", 0, 1000)
    with pytest.raises(ReglaCompraInvalida):
        LineaFactura("CAS", 1, 0)
    assert LineaFactura("CAS", Decimal("0.350"), 18000).subtotal == 6300  # granel
