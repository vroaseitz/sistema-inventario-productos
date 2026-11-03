"""Categorias en tabla (C-02): semilla, carga de la lista de la PO y sincronizacion."""

import sqlite3

import pytest

from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.dominio.categorias import CATEGORIAS_VALIDADAS
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_categorias import RepositorioCategoriasSQLite
from pos.infraestructura.sqlite.repositorio_historial import RepositorioHistorialSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.supabase.traductor import traducir_operacion


@pytest.fixture
def base():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    return con


def test_base_nueva_trae_las_20_categorias_validadas_en_orden(base):
    repo = RepositorioCategoriasSQLite(base)
    nombres = [c.nombre for c in repo.listar()]
    assert nombres == list(CATEGORIAS_VALIDADAS) and len(nombres) == 20
    assert [c.id for c in repo.listar()] == list(range(1, 21))
    assert nombres[6] == "Líquidos" and nombres[12] == "Panadería y repostería"
    crear_esquema(base)  # volver a abrir la base no duplica ni cambia nada
    assert len(repo.listar()) == 20


def _base_de_la_primera_version():
    """Una base como la de antes de CA-02: solo las 4 categorias antiguas, ids 1 a 4."""
    con = crear_conexion(":memory:")
    crear_esquema(con)
    con.execute("DELETE FROM categorias")
    con.execute("DELETE FROM sqlite_sequence WHERE name = 'categorias'")  # los ids vuelven a 1
    for nombre in ("frutas", "verduras", "abarrotes", "limpieza"):
        con.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
    return con


def test_base_antigua_pasa_a_las_20_y_mueve_frutas_y_verduras():
    con = _base_de_la_primera_version()
    productos = RepositorioProductosSQLite(con)
    for codigo, categoria_id in (("M1", 1), ("Z1", 2), ("A1", 3)):
        productos.guardar(Producto(codigo, codigo, Dinero(1000), UnidadVenta.UNIDAD, categoria_id))
    crear_esquema(con)  # al abrir la base se agregan las 20 y se retiran las antiguas
    repo = RepositorioCategoriasSQLite(con)
    nombres = [c.nombre for c in repo.listar()]
    assert nombres.count("Frutas y verduras") == 1
    # frutas y verduras no existen mas: sus productos pasaron a "Frutas y verduras"
    assert "frutas" not in nombres and "verduras" not in nombres and "limpieza" not in nombres
    assert repo.nombre_de(productos.obtener_por_codigo("M1").categoria_id) == "Frutas y verduras"
    assert repo.nombre_de(productos.obtener_por_codigo("Z1").categoria_id) == "Frutas y verduras"
    # 'abarrotes' no tiene equivalente y A1 la usa: no se pierde hasta reasignar el producto
    assert repo.nombre_de(productos.obtener_por_codigo("A1").categoria_id) == "abarrotes"
    productos.guardar(Producto("A1", "A1", Dinero(1000), UnidadVenta.UNIDAD, 6))  # 6 = Chocolates
    crear_esquema(con)
    assert "abarrotes" not in [c.nombre for c in repo.listar()]


def test_categoria_sin_nombre_se_rechaza(base):
    with pytest.raises(DatosProductoInvalidos):
        RepositorioCategoriasSQLite(base).agregar("   ")


def test_el_nombre_unico_lo_exige_la_base(base):
    with pytest.raises(sqlite3.IntegrityError):
        base.execute("INSERT INTO categorias (nombre) VALUES ('Plantas')")


def test_registrar_y_editar_producto_encolan_su_categoria_por_nombre(base):
    categorias = RepositorioCategoriasSQLite(base)
    productos = RepositorioProductosSQLite(base)
    cola = ColaSincronizacionSQLite(base)
    RegistrarProducto(productos, cola=cola, repositorio_categorias=categorias).ejecutar(
        "L1", "Leche", 1200, categoria_id=9
    )
    EditarProducto(
        productos, RepositorioHistorialSQLite(base), cola=cola, repositorio_categorias=categorias
    ).ejecutar("L1", "Leche entera", 1300, 9, "ana")  # antes la edicion no sincronizaba
    ops = [o for o in cola.pendientes() if o["entidad"] == "producto"]
    assert [(o["datos"]["nombre"], o["datos"]["precio"], o["datos"]["categoria"]) for o in ops] == [
        ("Leche", 1200, "Lácteos y huevos"),
        ("Leche entera", 1300, "Lácteos y huevos"),
    ]


def test_el_traductor_crea_la_categoria_remota_y_enlaza_el_producto():
    op = {
        "entidad": "producto",
        "operacion": "upsert",
        "datos": {
            "codigo": "L1",
            "nombre": "Leche",
            "precio": 1200,
            "unidad_venta": "unidad",
            "activo": True,
            "categoria": "Lácteos",
        },
        "id_cliente": "x",
    }
    sentencias = traducir_operacion(op)
    assert "INSERT INTO pos.categoria" in sentencias[0][0] and sentencias[0][1] == ("Lácteos",)
    assert "categoria_id = EXCLUDED.categoria_id" in sentencias[1][0]
    sin = traducir_operacion({**op, "datos": {**op["datos"], "categoria": None}})
    assert len(sin) == 1 and "Sin categoria" in sin[0][0]  # compatibilidad con lo ya encolado
