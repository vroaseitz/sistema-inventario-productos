"""Categorias en tabla (C-02): semilla, carga de la lista de la PO y sincronizacion."""

import sqlite3

import pytest

from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.dominio.errores import DatosProductoInvalidos
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


def test_base_nueva_trae_las_cuatro_categorias_con_sus_ids_de_siempre(base):
    repo = RepositorioCategoriasSQLite(base)
    assert [(c.id, c.nombre) for c in repo.listar()] == [
        (1, "frutas"),
        (2, "verduras"),
        (3, "abarrotes"),
        (4, "limpieza"),
    ]
    crear_esquema(base)  # volver a abrir la base no duplica ni cambia nada
    assert len(repo.listar()) == 4


def test_sembrar_agrega_solo_las_que_faltan_y_no_toca_las_existentes(base):
    repo = RepositorioCategoriasSQLite(base)
    creadas = repo.sembrar(["Lácteos", "FRUTAS", "  Panadería  ", "lacteos"])
    assert creadas == 2  # FRUTAS ya existe; 'lacteos' es la misma que 'Lácteos'
    assert [c.nombre for c in repo.listar()][:4] == ["frutas", "verduras", "abarrotes", "limpieza"]
    assert repo.nombre_de(5) == "Lácteos" and repo.nombre_de(6) == "Panadería"
    assert repo.nombre_de(99) is None and repo.nombre_de(None) is None


def test_categoria_sin_nombre_se_rechaza(base):
    with pytest.raises(DatosProductoInvalidos):
        RepositorioCategoriasSQLite(base).agregar("   ")


def test_el_nombre_unico_lo_exige_la_base(base):
    with pytest.raises(sqlite3.IntegrityError):
        base.execute("INSERT INTO categorias (nombre) VALUES ('frutas')")


def test_registrar_y_editar_producto_encolan_su_categoria_por_nombre(base):
    categorias = RepositorioCategoriasSQLite(base)
    categorias.sembrar(["Lácteos"])
    productos = RepositorioProductosSQLite(base)
    cola = ColaSincronizacionSQLite(base)
    RegistrarProducto(productos, cola=cola, repositorio_categorias=categorias).ejecutar(
        "L1", "Leche", 1200, categoria_id=5
    )
    EditarProducto(
        productos, RepositorioHistorialSQLite(base), cola=cola, repositorio_categorias=categorias
    ).ejecutar("L1", "Leche entera", 1300, 5, "ana")  # antes la edicion no sincronizaba
    ops = [o for o in cola.pendientes() if o["entidad"] == "producto"]
    assert [(o["datos"]["nombre"], o["datos"]["precio"], o["datos"]["categoria"]) for o in ops] == [
        ("Leche", 1200, "Lácteos"),
        ("Leche entera", 1300, "Lácteos"),
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
