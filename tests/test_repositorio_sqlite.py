"""Pruebas de regresion QA para el repositorio SQLite de productos.

Cubre el hallazgo:
- QA C-05b: persistencia y reconstruccion completa (costo, perecible, dias_aviso)
  al guardar y volver a leer un producto desde la base de datos.
"""

from __future__ import annotations

import pytest

from pos.dominio.productos import Producto
from pos.dominio.value_objects import Costo, Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite


@pytest.fixture
def conexion_memoria():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    yield con
    con.close()


@pytest.fixture
def repositorio(conexion_memoria):
    return RepositorioProductosSQLite(conexion_memoria)


class TestGuardadoCompletoProducto:
    def test_persiste_costo_perecible_y_dias_aviso(self, repositorio):
        producto = Producto(
            codigo="P-100",
            nombre="Yogurt Natural 1L",
            precio=Dinero(1200),
            categoria_id=3,
            costo=Costo(neto=Dinero(800), iva=Dinero(152)),
            perecible=True,
            dias_aviso=5,
        )

        repositorio.guardar(producto)
        recuperado = repositorio.obtener_por_codigo("P-100")

        assert recuperado is not None
        assert recuperado.costo is not None
        assert recuperado.costo.neto.monto == 800
        assert recuperado.perecible is True
        assert recuperado.dias_aviso == 5

    def test_producto_sin_costo_reconstruye_con_costo_none(self, repositorio):
        producto = Producto(
            codigo="P-400",
            nombre="Bolsa Reutilizable",
            precio=Dinero(500),
            categoria_id=4,
            costo=None,
            perecible=False,
            dias_aviso=None,
        )

        repositorio.guardar(producto)
        recuperado = repositorio.obtener_por_codigo("P-400")

        assert recuperado is not None
        assert recuperado.costo is None
        assert recuperado.perecible is False
        assert recuperado.dias_aviso is None

    def test_reconstruccion_sobrevive_ciclo_guardar_obtener(self, repositorio):
        producto = Producto(
            codigo="P-200",
            nombre="Cereal Integral",
            precio=Dinero(4500),
            categoria_id=2,
            costo=Costo(neto=Dinero(3000), iva=Dinero(570)),
            perecible=False,
            dias_aviso=None,
        )

        repositorio.guardar(producto)
        recuperado = repositorio.obtener_por_codigo("P-200")

        assert recuperado.costo is not None
        assert recuperado.costo.neto.monto == 3000
        assert recuperado.perecible is False
        assert recuperado.dias_aviso is None

    def test_listar_reconstruye_producto_completo(self, repositorio):
        producto = Producto(
            codigo="P-300",
            nombre="Leche Descremada",
            precio=Dinero(990),
            categoria_id=1,
            costo=Costo(neto=Dinero(700), iva=Dinero(133)),
            perecible=True,
            dias_aviso=3,
        )

        repositorio.guardar(producto)
        listado = repositorio.listar()

        assert len(listado) == 1
        assert listado[0].codigo == "P-300"
        assert listado[0].costo is not None
        assert listado[0].costo.neto.monto == 700
        assert listado[0].perecible is True
        assert listado[0].dias_aviso == 3
