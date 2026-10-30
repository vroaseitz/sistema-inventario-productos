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


class TestOrdenBusqueda:
    def test_orden_busqueda_prioriza_inicio(self, repositorio):
        """QA C-15: los que EMPIEZAN con el termino van primero, luego los que solo lo contienen."""
        repositorio.guardar(Producto(codigo="A-1", nombre="Aceite", precio=Dinero(2000), categoria_id=1))
        repositorio.guardar(Producto(codigo="T-1", nombre="Té verde", precio=Dinero(1500), categoria_id=1))
        repositorio.guardar(Producto(codigo="B-1", nombre="Botella de vidrio", precio=Dinero(3000), categoria_id=1))

        resultados = repositorio.buscar("te")

        assert len(resultados) == 3
        nombres = [p.nombre for p in resultados]
        # Empieza con "te" (normalizado): "Té verde".
        assert nombres[0] == "Té verde"
        # Solo contienen "te": van despues, ordenados alfabeticamente
        # ("Aceite" < "Botella...").
        assert nombres[1] == "Aceite"
        assert nombres[2] == "Botella de vidrio"


@pytest.fixture
def conexion_memoria():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    yield con
    con.close()


@pytest.fixture
def repositorio(conexion_memoria):
    return RepositorioProductosSQLite(conexion_memoria)


class TestCategoriasDesdeBD:
    def test_esquema_crea_tabla_categoria_con_seed(self, conexion_memoria):
        """La tabla categoria existe y viene sembrada con las 4 categorias."""
        filas = conexion_memoria.execute("SELECT id, nombre FROM categoria ORDER BY id").fetchall()
        assert [(f["id"], f["nombre"]) for f in filas] == [
            (1, "frutas"),
            (2, "verduras"),
            (3, "abarrotes"),
            (4, "limpieza"),
        ]

    def test_listar_categorias_desde_bd(self, repositorio):
        # La PO podra agregar una categoria en BD y la GUI la verá sin cambiar codigo.
        repositorio._con.execute("INSERT INTO categoria (nombre) VALUES ('panaderia')")

        nombres = [c.nombre for c in repositorio.listar_categorias()]

        assert nombres == ["frutas", "verduras", "abarrotes", "limpieza", "panaderia"]

    def test_crear_categoria(self, repositorio):
        repositorio.crear_categoria("panaderia")

        nombres = [c.nombre for c in repositorio.listar_categorias()]
        assert "panaderia" in nombres
        # Idempotente: crear dos veces la misma no duplica.
        with pytest.raises(Exception):
            repositorio.crear_categoria("panaderia")


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
        # El IVA guardado NO es 19% del neto a proposito: si el repositorio
        # recalculara el impuesto al reconstruir, el total quedaria inflado
        # (1000 + 190 = 1190) y el neto no coincidiria con el guardado.
        producto = Producto(
            codigo="P-200",
            nombre="Cereal Integral",
            precio=Dinero(4500),
            categoria_id=2,
            costo=Costo(neto=Dinero(1000), iva=Dinero(0)),
            perecible=False,
            dias_aviso=None,
        )

        repositorio.guardar(producto)
        recuperado = repositorio.obtener_por_codigo("P-200")

        assert recuperado.costo is not None
        # QA C-05b: el neto se recupera EXACTAMENTE como se guardo, sin
        # inflarse con recalculos de IVA (ni el neto ni el total cambian).
        assert recuperado.costo.neto.monto == producto.costo.neto.monto
        assert recuperado.costo.neto.monto == 1000
        assert recuperado.costo.total.monto == 1000
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
        assert listado[0].costo.total.monto == 700
        assert listado[0].perecible is True
        assert listado[0].dias_aviso == 3
