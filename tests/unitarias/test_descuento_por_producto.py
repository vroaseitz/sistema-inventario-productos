"""O-42: el descuento por vencimiento se puede ajustar por producto (QA 18-11)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento
from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.lotes import Lote
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_historial import RepositorioHistorialSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite


@pytest.fixture
def con(tmp_path):
    c = crear_conexion(str(tmp_path / "d.db"))
    crear_esquema(c)
    return c


def test_sin_ajustes_un_producto_usa_la_politica_por_defecto():
    p = Producto("A", "Algo", Dinero(1000), categoria_id=1)
    assert p.politica_descuento().porcentaje(14) == 20
    assert p.politica_descuento().porcentaje(7) == 50


def test_ajustes_se_guardan_y_se_leen(con):
    repo = RepositorioProductosSQLite(con)
    RegistrarProducto(repo).ejecutar(
        "PAN", "Pan", 2000, categoria_id=1, desc_dias_1=3, desc_dias_2=1, desc_pct_2=60
    )
    pan = repo.obtener_por_codigo("PAN")
    assert (pan.desc_dias_1, pan.desc_pct_1, pan.desc_dias_2, pan.desc_pct_2) == (3, None, 1, 60)
    politica = pan.politica_descuento()
    assert politica.porcentaje(3) == 20 and politica.porcentaje(1) == 60
    assert politica.porcentaje(5) == 0  # fuera de la primera etapa del pan


def test_ajustes_incoherentes_no_se_guardan(con):
    repo = RepositorioProductosSQLite(con)
    with pytest.raises(DatosProductoInvalidos):
        RegistrarProducto(repo).ejecutar("X", "X", 1000, categoria_id=1, desc_pct_1=150)
    assert repo.obtener_por_codigo("X") is None


def test_editar_cambia_y_vaciar_vuelve_al_defecto(con):
    repo = RepositorioProductosSQLite(con)
    RegistrarProducto(repo).ejecutar("Q", "Queso", 5000, categoria_id=1)
    editar = EditarProducto(repo, RepositorioHistorialSQLite(con))
    editar.ejecutar("Q", "Queso", 5000, 1, "t", desc_dias_1=30, desc_pct_1=15)
    assert repo.obtener_por_codigo("Q").politica_descuento().porcentaje(25) == 15
    editar.ejecutar("Q", "Queso", 5000, 1, "t")  # campos vacios
    q = repo.obtener_por_codigo("Q")
    assert q.desc_dias_1 is None and q.politica_descuento().porcentaje(25) == 0
    with pytest.raises(DatosProductoInvalidos):
        editar.ejecutar("Q", "Queso", 5000, 1, "t", desc_dias_1=5)  # etapa 1 < etapa final (7)
    assert repo.obtener_por_codigo("Q").desc_dias_1 is None  # nada quedo a medias


def test_f3_alertas_usa_las_etapas_del_producto(con):
    productos = RepositorioProductosSQLite(con)
    lotes = RepositorioLotesSQLite(con)
    RegistrarProducto(productos).ejecutar(
        "PAN",
        "Pan",
        2000,
        categoria_id=1,
        perecible=True,
        dias_aviso=3,
        desc_dias_1=3,
        desc_dias_2=1,
    )
    hoy = date.today()
    lotes.guardar(Lote("PAN", hoy + timedelta(days=1), Decimal(5)))
    alertas = ConsultarAlertasVencimiento(lotes, productos).ejecutar(hoy)
    assert [a.descuento_pct for a in alertas] == [50]
