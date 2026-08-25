"""Pruebas de integracion de los repositorios contra SQLite real (base en memoria)."""

from decimal import Decimal

import pytest

from pos.dominio.inventario import Existencia
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite


@pytest.fixture
def conexion():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    yield con
    con.close()


def test_guardar_y_obtener_producto(conexion):
    repo = RepositorioProductosSQLite(conexion)
    repo.guardar(Producto("12345", "Nueces", Dinero(8000), unidad_venta=UnidadVenta.GRANEL))
    recuperado = repo.obtener_por_codigo("12345")
    assert recuperado is not None
    assert recuperado.nombre == "Nueces"
    assert recuperado.es_granel is True
    assert recuperado.precio.monto == 8000


def test_upsert_actualiza_producto(conexion):
    repo = RepositorioProductosSQLite(conexion)
    repo.guardar(Producto("1", "Arroz", Dinero(1000)))
    repo.guardar(Producto("1", "Arroz 1kg", Dinero(1200)))
    p = repo.obtener_por_codigo("1")
    assert p.nombre == "Arroz 1kg"
    assert p.precio.monto == 1200
    assert len(repo.listar()) == 1


def test_producto_inexistente_devuelve_none(conexion):
    repo = RepositorioProductosSQLite(conexion)
    assert repo.obtener_por_codigo("nope") is None


def test_existencias_persisten_decimales(conexion):
    RepositorioProductosSQLite(conexion).guardar(Producto("12345", "Nueces", Dinero(8000)))
    repo = RepositorioExistenciasSQLite(conexion)
    repo.guardar(Existencia("12345", Decimal("2.750")))
    e = repo.obtener("12345")
    assert e.cantidad == Decimal("2.750")
