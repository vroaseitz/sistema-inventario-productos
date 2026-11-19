"""CA-22: eliminar un producto creado por error; con historia no se elimina (QA 18-11)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.eliminar_producto import EliminarProducto, ProductoConHistoria
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.dominio.errores import DatosProductoInvalidos
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.supabase.traductor import traducir_operacion


@pytest.fixture
def mundo(tmp_path):
    con = crear_conexion(str(tmp_path / "e.db"))
    crear_esquema(con)
    repo = RepositorioProductosSQLite(con)
    cola = ColaSincronizacionSQLite(con)
    RegistrarProducto(repo).ejecutar("ERR", "Creado por error", 1000, categoria_id=1)
    RegistrarProducto(repo).ejecutar("VIVO", "Con historia", 1000, categoria_id=1)
    existencias = RepositorioExistenciasSQLite(con)
    IngresarStock(repo, existencias, RepositorioLotesSQLite(con)).ejecutar("VIVO", 5, "Compra")
    return repo, EliminarProducto(repo, cola), cola, existencias


def test_producto_sin_historia_se_elimina_y_se_encola_el_borrado(mundo):
    repo, eliminar, cola, _ = mundo
    assert eliminar.puede_eliminarse("ERR")
    eliminar.ejecutar("ERR")
    assert repo.obtener_por_codigo("ERR") is None
    assert [p["entidad"] for p in cola.pendientes()] == ["producto_eliminar"]


def test_producto_con_stock_no_se_elimina(mundo):
    repo, eliminar, _, _ = mundo
    assert not eliminar.puede_eliminarse("VIVO")
    with pytest.raises(ProductoConHistoria, match="desactivar"):
        eliminar.ejecutar("VIVO")
    assert repo.obtener_por_codigo("VIVO") is not None


def test_producto_con_lote_no_se_elimina(mundo):
    repo, eliminar, _, _ = mundo
    RegistrarProducto(repo).ejecutar(
        "PER", "Perecible", 900, categoria_id=1, perecible=True, dias_aviso=7
    )
    IngresarStock(
        repo, RepositorioExistenciasSQLite(repo._con), RepositorioLotesSQLite(repo._con)
    ).ejecutar("PER", Decimal(1), "Compra", date.today() + timedelta(days=30))
    with pytest.raises(ProductoConHistoria):
        eliminar.ejecutar("PER")


def test_producto_inexistente(mundo):
    with pytest.raises(DatosProductoInvalidos):
        mundo[1].ejecutar("NO-EXISTE")


def test_el_traductor_borra_solo_si_no_hay_historia():
    sentencias = traducir_operacion(
        {"entidad": "producto_eliminar", "operacion": "delete", "datos": {"codigo": "ERR"}}
    )
    assert len(sentencias) == 2
    for sql, params in sentencias:
        assert params == ("ERR",)
        for tabla in ("venta_detalle", "lote", "factura_compra_detalle"):
            assert f"pos.{tabla}" in sql  # las guardas de historia estan en cada sentencia
