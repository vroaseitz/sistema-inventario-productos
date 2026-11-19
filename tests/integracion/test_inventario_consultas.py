"""HU-INV-05 stock minimo, HU-INV-07 inventario valorizado y HU-INV-08 movimientos."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.consultar_inventario import (
    ConsultarExistencias,
    ConsultarMovimientos,
    DefinirStockMinimo,
    ReporteInventario,
)
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.casos_uso.registrar_factura_compra import RegistrarFacturaCompra
from pos.aplicacion.casos_uso.registrar_merma import RegistrarMerma
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.registro_movimientos import RegistroMovimientos
from pos.dominio.compras import FacturaCompra, LineaFactura, iva_de
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.inventario import Existencia, MotivoAjuste, TipoMovimiento
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
from pos.infraestructura.sqlite.repositorio_existencias import (
    RepositorioAjustesSQLite,
    RepositorioExistenciasSQLite,
)
from pos.infraestructura.sqlite.repositorio_facturas_compra import RepositorioFacturasCompraSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_movimientos import RepositorioMovimientosSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite

HOY = date.today()


def costo(n):
    return Costo(neto=Dinero(n), iva=Dinero(0))


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
        movs = RepositorioMovimientosSQLite(con)
        auditoria = RepositorioAuditoriaSQLite(con)
        facturas = RepositorioFacturasCompraSQLite(con)
        quien = "mostrador"

    a = A()
    registro = RegistroMovimientos(a.movs, lambda: a.quien)
    a.registro = registro
    a.ingresar = IngresarStock(a.productos, a.existencias, a.lotes, movimientos=registro)
    a.venta = RegistrarVenta(a.ventas, a.turnos, a.productos, a.existencias, movimientos=registro)
    a.merma = RegistrarMerma(
        a.existencias, RepositorioAjustesSQLite(con), a.lotes, movimientos=registro
    )
    a.consultar = ConsultarExistencias(a.productos, a.existencias, a.ventas)
    a.reporte = ReporteInventario(a.productos, a.existencias)
    a.historial = ConsultarMovimientos(a.movs, a.productos)
    for codigo, nombre, precio, c, minimo in (
        ("ALM", "Almendra", 4000, 2940, 10),
        ("CAS", "Castana", 15000, 11765, 6),
        ("KOM", "Kombucha", 3000, 1610, 8),
        ("CRE", "Crema de mani", 5000, None, 4),
    ):
        a.productos.guardar(
            Producto(
                codigo,
                nombre,
                Dinero(precio),
                categoria_id=1,
                costo=costo(c) if c else None,
                stock_minimo=minimo,
            )
        )
    a.productos.guardar(
        Producto(
            "QUI",
            "Quinoa a granel",
            Dinero(9000),
            UnidadVenta.GRANEL,
            categoria_id=2,
            costo=costo(5000),
        )
    )
    for codigo, cantidad in (("ALM", 31), ("CAS", 14), ("KOM", 2), ("CRE", 0), ("QUI", "12.5")):
        a.existencias.guardar(Existencia(codigo, Decimal(str(cantidad))))
    AbrirTurnoCaja(a.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    return a


def test_existencias_por_urgencia_con_agotado_bajo_minimo_normal_y_granel(app):
    filas = app.consultar.ejecutar()
    assert [(f.codigo, f.estado) for f in filas] == [
        ("CRE", "Agotado"),
        ("KOM", "Bajo el mínimo"),
        ("ALM", "Normal"),
        ("CAS", "Normal"),
        ("QUI", "Granel"),
    ]
    assert filas[-1].existencia == Decimal("12.5") and filas[-1].granel


def test_filtros_de_existencias(app):
    assert [f.codigo for f in app.consultar.ejecutar(mostrar="Bajo el mínimo")] == ["KOM"]
    assert [f.codigo for f in app.consultar.ejecutar(mostrar="Agotados")] == ["CRE"]
    assert [f.codigo for f in app.consultar.ejecutar(buscar="CASTAÑA")] == ["CAS"]  # sin tildes
    assert [f.codigo for f in app.consultar.ejecutar(categoria_id=2)] == ["QUI"]
    assert [f.nombre for f in app.consultar.ejecutar(orden="Nombre")][0] == "Almendra"


def test_un_producto_justo_en_el_minimo_no_esta_bajo_el_minimo(app):
    app.existencias.guardar(Existencia("KOM", Decimal("8")))
    assert next(f for f in app.consultar.ejecutar() if f.codigo == "KOM").estado == "Normal"


def test_la_ultima_venta_y_los_inactivos(app):
    v = app.venta.iniciar(usuario_id=1)
    app.venta.agregar_producto(v, "CAS", 2)
    app.venta.agregar_pago(v, Pago(MedioPago.TARJETA, Dinero(v.total.monto)))
    app.venta.cerrar(v)
    cas = next(f for f in app.consultar.ejecutar() if f.codigo == "CAS")
    assert cas.ultima_venta == HOY and cas.existencia == 12
    producto = app.productos.obtener_por_codigo("ALM")
    producto.activo = False
    app.productos.guardar(producto)
    assert "ALM" not in [f.codigo for f in app.consultar.ejecutar()]


def test_definir_stock_minimo_valida_y_audita(app):
    auditor = Auditor(app.auditoria, lambda: "roxana")
    definir = DefinirStockMinimo(app.productos, auditor)
    definir.ejecutar("CRE", 12)
    assert app.productos.obtener_por_codigo("CRE").stock_minimo == 12
    assert next(f for f in app.consultar.ejecutar() if f.codigo == "CRE").estado == "Agotado"
    registro = app.auditoria.listar()[0]
    assert (registro["accion"], registro["antes"], registro["despues"]) == (
        "Cambio de stock mínimo",
        "4",
        "12",
    )
    definir.ejecutar("CRE", None)
    assert app.productos.obtener_por_codigo("CRE").stock_minimo is None
    with pytest.raises(DatosProductoInvalidos, match="negativo"):
        definir.ejecutar("CRE", -1)
    with pytest.raises(DatosProductoInvalidos, match="granel"):
        definir.ejecutar("QUI", 5)
    with pytest.raises(DatosProductoInvalidos, match="No existe"):
        definir.ejecutar("XXX", 5)


def test_inventario_valorizado_a_costo_excluye_granel_y_costo_pendiente(app):
    resumen = app.reporte.ejecutar()
    por_codigo = {f.codigo: f for f in resumen.filas}
    assert por_codigo["ALM"].valor == 31 * 2940 == 91140
    assert por_codigo["CAS"].valor == 14 * 11765 == 164710
    assert por_codigo["KOM"].valor == 3220
    assert por_codigo["CRE"].exclusion == "costo pendiente" and por_codigo["CRE"].valor is None
    assert por_codigo["QUI"].exclusion == "no valorizable"
    assert resumen.total == 91140 + 164710 + 3220  # sin la crema ni la quinoa
    assert {f.codigo for f in resumen.excluidas} == {"CRE", "QUI"}
    assert resumen.filas[-1].exclusion and resumen.filas[0].codigo == "CAS"  # mayor valor primero


def test_valorizar_a_precio_de_venta_y_filtro_de_activos(app):
    resumen = app.reporte.ejecutar(valorizar_a="Precio de venta")
    assert {f.codigo: f.valor for f in resumen.filas}["CRE"] == 0  # tiene precio, existencia 0
    producto = app.productos.obtener_por_codigo("CAS")
    producto.activo = False
    app.productos.guardar(producto)
    assert "CAS" not in {f.codigo for f in app.reporte.ejecutar().filas}
    assert "CAS" in {f.codigo for f in app.reporte.ejecutar(incluir="Todos").filas}


def test_el_historial_registra_entrada_venta_y_merma_con_usuario(app):
    app.ingresar.ejecutar("ALM", 20, "Compra a proveedor")
    app.quien = "ana"
    v = app.venta.iniciar(usuario_id=1)
    app.venta.agregar_producto(v, "ALM", 3)
    app.venta.agregar_pago(v, Pago(MedioPago.TARJETA, Dinero(v.total.monto)))
    app.venta.cerrar(v)
    app.quien = "germaine"
    app.merma.ejecutar("ALM", 2, MotivoAjuste.VENCIMIENTO, "germaine")
    filas = app.historial.ejecutar(HOY, HOY)
    resumen = [(m.tipo.value, m.cantidad, m.motivo, m.usuario, nombre) for m, nombre in filas]
    assert resumen == [  # el mas reciente primero
        ("merma", Decimal("-2"), "Vencimiento", "germaine", "Almendra"),
        ("venta", Decimal("-3"), f"Ticket {v.id}", "ana", "Almendra"),
        ("entrada", Decimal("20"), "Compra a proveedor", "mostrador", "Almendra"),
    ]
    assert [m.tipo for m, _ in app.historial.ejecutar(HOY, HOY, TipoMovimiento.VENTA)] == [
        TipoMovimiento.VENTA
    ]
    assert app.historial.ejecutar(HOY + timedelta(days=1), HOY + timedelta(days=2)) == []
    assert app.historial.ejecutar(HOY, HOY, codigo="CAS") == []
    with pytest.raises(ValueError):
        app.historial.ejecutar(HOY, HOY - timedelta(days=1))


def test_una_factura_de_compra_deja_una_entrada_con_su_numero(app):
    caso = RegistrarFacturaCompra(
        app.facturas, app.productos, app.existencias, app.lotes, movimientos=app.registro
    )
    linea = LineaFactura("ALM", 10, 2000)
    caso.confirmar(FacturaCompra("Andes", "F-4502", HOY, 20000, iva_de(20000), [linea]))
    movimiento, _ = app.historial.ejecutar(HOY, HOY)[0]
    assert (movimiento.tipo, movimiento.cantidad, movimiento.motivo) == (
        TipoMovimiento.ENTRADA,
        Decimal("10"),
        "Factura F-4502",
    )
