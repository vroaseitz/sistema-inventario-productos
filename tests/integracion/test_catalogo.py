"""F2 Catalogo: lista con filtros, categorias (CA-16) e historial de precios (SQLite real)."""

from datetime import date
from decimal import Decimal

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.consultar_catalogo import (
    ConsultarCatalogo,
    ConsultarCategorias,
    motivo_de_revision,
)
from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.gestionar_categorias import GestionarCategorias
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
from pos.infraestructura.sqlite.repositorio_categorias import RepositorioCategoriasSQLite
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_historial import RepositorioHistorialSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite


def costo(n):
    return Costo(neto=Dinero(n), iva=Dinero(0))


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        categorias = RepositorioCategoriasSQLite(con)
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        historial = RepositorioHistorialSQLite(con)
        ventas = RepositorioVentasSQLite(con)
        turnos = RepositorioTurnosCajaSQLite(con)
        cola = ColaSincronizacionSQLite(con)
        auditoria = RepositorioAuditoriaSQLite(con)

    a = A()
    a.auditor = Auditor(a.auditoria, lambda: "roxana")
    a.gestion = GestionarCategorias(a.categorias, a.productos, a.cola, a.auditor)
    a.catalogo = ConsultarCatalogo(a.productos, a.existencias, a.categorias)
    a.nombres = ConsultarCategorias(a.categorias, a.productos, a.ventas)
    frutos = a.categorias.listar()[0].id  # «Frutos secos y semillas»
    harinas = a.categorias.listar()[1].id
    a.frutos, a.harinas = frutos, harinas
    for codigo, nombre, cat, precio, c in (
        ("CAS", "Castaña de cajú 1 kilo", frutos, 22220, 14000),
        ("ACE", "Aceite de coco 200 ml", harinas, 5000, 3000),
        ("TE", "Té verde hojas 100 g", frutos, 3500, 2000),
        ("MIE", "Miel Quillay 1 K", frutos, 11990, 5),  # costo sospechoso
        ("CRE", "Crema de maní", harinas, 6590, None),  # sin costo
    ):
        a.productos.guardar(
            Producto(
                codigo, nombre, Dinero(precio), categoria_id=cat, costo=costo(c) if c else None
            )
        )
        a.existencias.guardar(Existencia(codigo, Decimal("10")))
    a.productos.guardar(
        Producto("QUI", "Quinoa a granel", Dinero(6900), UnidadVenta.GRANEL, categoria_id=harinas)
    )
    return a


def test_busqueda_sin_tildes_y_lo_que_empieza_primero(app):
    filas = app.catalogo.ejecutar(buscar="te")
    # «Té verde» empieza con «te»; «Aceite de coco» y «Castaña de cajú» solo lo contienen
    assert filas[0].codigo == "TE"
    assert "CAS" not in [f.codigo for f in app.catalogo.ejecutar(buscar="castana x")]
    assert [f.codigo for f in app.catalogo.ejecutar(buscar="CASTANA")] == ["CAS"]  # sin tildes
    assert [f.codigo for f in app.catalogo.ejecutar(buscar="quillay")] == ["MIE"]


def test_filtros_de_categoria_estado_y_costo(app):
    assert {f.codigo for f in app.catalogo.ejecutar(categoria_id=app.harinas)} == {
        "ACE",
        "CRE",
        "QUI",
    }
    assert {f.codigo for f in app.catalogo.ejecutar(costo="Sin costo")} == {"CRE", "QUI"}
    producto = app.productos.obtener_por_codigo("ACE")
    producto.activo = False
    app.productos.guardar(producto)
    assert "ACE" not in [f.codigo for f in app.catalogo.ejecutar()]
    assert [f.codigo for f in app.catalogo.ejecutar(estado="Inactivos")] == ["ACE"]
    assert len(app.catalogo.ejecutar(estado="Todos")) == 6


def test_granel_y_valores_sospechosos_se_marcan_para_revisar(app):
    por_codigo = {f.codigo: f for f in app.catalogo.ejecutar()}
    assert por_codigo["QUI"].existencia == "granel" and por_codigo["QUI"].granel
    assert por_codigo["CAS"].existencia == "10" and por_codigo["CAS"].estado == "Activo"
    assert por_codigo["MIE"].estado == "Revisar"
    assert "coma corrida" in motivo_de_revision(app.productos.obtener_por_codigo("MIE"))
    assert motivo_de_revision(app.productos.obtener_por_codigo("CAS")) == ""


def test_crear_y_renombrar_categoria_con_reglas(app):
    nueva = app.gestion.crear("Mascotas")
    assert nueva.activa
    with pytest.raises(DatosProductoInvalidos, match="Ya existe una categoría llamada Mascotas"):
        app.gestion.crear("  mascotas ")
    app.gestion.renombrar(nueva.id, "Mascotas y animales")
    assert app.categorias.nombre_de(nueva.id) == "Mascotas y animales"
    with pytest.raises(DatosProductoInvalidos, match="Fusionar"):
        app.gestion.renombrar(nueva.id, "Plantas")  # ya existe: se propone fusionar
    acciones = [f["accion"] for f in app.auditoria.listar()]
    assert acciones == ["Renombrar categoría", "Nueva categoría"]


def test_renombrar_reenvia_los_productos_con_el_nombre_nuevo(app):
    app.cola.pendientes()  # vacia al inicio
    app.gestion.renombrar(app.harinas, "Harinas, legumbres y granos")
    enviados = [o["datos"] for o in app.cola.pendientes() if o["entidad"] == "producto"]
    assert {d["codigo"] for d in enviados} == {"ACE", "CRE", "QUI"}
    assert all(d["categoria"] == "Harinas, legumbres y granos" for d in enviados)


def test_fusionar_mueve_productos_elimina_el_origen_y_audita(app):
    origen = app.gestion.crear("Varios")
    producto = app.productos.obtener_por_codigo("TE")
    producto.categoria_id = origen.id
    app.productos.guardar(producto)
    movidos = app.gestion.fusionar(origen.id, app.frutos)
    assert movidos == 1
    assert app.productos.obtener_por_codigo("TE").categoria_id == app.frutos
    assert app.categorias.obtener(origen.id) is None
    registro = app.auditoria.listar()[0]
    assert registro["accion"] == "Fusión de categorías"
    assert registro["registro"] == "Varios → Frutos secos y semillas"
    assert registro["detalle"]["productos_movidos"] == 1
    with pytest.raises(DatosProductoInvalidos, match="la misma"):
        app.gestion.fusionar(app.frutos, app.frutos)


def test_desactivar_categoria_la_saca_del_selector_sin_tocar_productos(app):
    app.gestion.cambiar_estado(app.harinas, False)
    assert app.harinas not in [c.id for c in app.categorias.listar(solo_activas=True)]
    assert app.productos.obtener_por_codigo("ACE").categoria_id == app.harinas  # sigue ahi
    app.gestion.cambiar_estado(app.harinas, True)
    assert app.harinas in [c.id for c in app.categorias.listar(solo_activas=True)]


def test_categorias_con_productos_y_venta_del_mes(app):
    AbrirTurnoCaja(app.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    venta = RegistrarVenta(app.ventas, app.turnos, app.productos, app.existencias)
    v = venta.iniciar(usuario_id=1)
    venta.agregar_producto(v, "CAS", 1)
    venta.agregar_producto(v, "ACE", 2)
    venta.agregar_pago(v, Pago(MedioPago.TARJETA, Dinero(v.total.monto)))
    venta.cerrar(v)
    filas = {f.id: f for f in app.nombres.ejecutar(date.today())}
    assert filas[app.frutos].productos == 3 and filas[app.frutos].venta_mes == 22220
    assert filas[app.harinas].venta_mes == 10000
    assert filas[app.frutos].participacion == pytest.approx(22220 / 32220)


def test_el_historial_de_precios_guarda_motivo_y_usuaria(app):
    editar = EditarProducto(app.productos, app.historial, auditor=app.auditor)
    editar.ejecutar(
        "CAS",
        "Castaña de cajú 1 kilo",
        23000,
        app.frutos,
        "roxana",
        14000,
        motivo_precio="Ajuste por alza de costo",
    )
    editar.ejecutar("CAS", "Castaña de cajú 1 kilo", 23500, app.frutos, "roxana", 14000)
    registros = app.historial.listar_por_producto("CAS")
    assert [(r.precio_anterior.monto, r.precio_nuevo.monto, r.motivo) for r in registros] == [
        (23000, 23500, ""),
        (22220, 23000, "Ajuste por alza de costo"),
    ]
    assert app.historial.listar_por_producto("ACE") == []


def test_no_se_fusiona_hacia_una_categoria_desactivada(app):
    origen = app.gestion.crear("Varios")
    app.gestion.cambiar_estado(app.harinas, False)
    with pytest.raises(DatosProductoInvalidos, match="desactivada"):
        app.gestion.fusionar(origen.id, app.harinas)
    assert app.categorias.obtener(origen.id) is not None  # el origen no se toco
