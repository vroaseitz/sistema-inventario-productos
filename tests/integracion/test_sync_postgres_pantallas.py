# ruff: noqa: F811
"""Lo que agregaron las pantallas nuevas llega a PostgreSQL REAL (schema `pos`, migracion 007).

Costo, perecible, dias de aviso y existencia minima del producto; categorias (crear, desactivar,
renombrar, fusionar); nota de la venta y motivo del descuento; codigo impreso del lote.
Se omite sin POS_TEST_PG_URL (ver test_sync_postgres.py: usa Docker local, nunca Supabase real).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

pytest.importorskip("psycopg2")

from pos.aplicacion.casos_uso.consultar_inventario import DefinirStockMinimo  # noqa: E402
from pos.aplicacion.casos_uso.gestionar_categorias import GestionarCategorias  # noqa: E402
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock  # noqa: E402
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto  # noqa: E402
from pos.dominio.pagos import MedioPago, Pago  # noqa: E402
from pos.dominio.productos import UnidadVenta  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.infraestructura.sqlite.repositorio_categorias import (  # noqa: E402
    RepositorioCategoriasSQLite,
)
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite  # noqa: E402
from tests.integracion.test_sync_postgres import PG_URL, App, _uno, pg  # noqa: E402,F401

pytestmark = pytest.mark.skipif(
    not PG_URL, reason="define POS_TEST_PG_URL para probar contra PostgreSQL"
)


def _fila(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()


def test_producto_llega_con_costo_perecible_dias_y_minimo(pg):
    app = App()
    categorias = RepositorioCategoriasSQLite(app.productos._con)
    registrar = RegistrarProducto(app.productos, cola=app.cola, repositorio_categorias=categorias)
    registrar.ejecutar(
        "YOG",
        "Yogurt natural",
        2000,
        UnidadVenta.UNIDAD,
        9,
        costo=1200,
        perecible=True,
        dias_aviso=7,
    )
    DefinirStockMinimo(app.productos, cola=app.cola, repositorio_categorias=categorias).ejecutar(
        "YOG", 6
    )

    assert app.sincronizar().fallo_en is None
    costo, cargado, perecible, dias, minimo = _fila(
        pg,
        "SELECT costo_neto, costo_cargado, es_perecible, dias_aviso_vencimiento, stock_minimo "
        "FROM pos.producto WHERE codigo = 'YOG'",
    )
    assert (costo, cargado, perecible, dias, minimo) == (Decimal("1200.00"), True, True, 7, 6)


def test_categorias_crear_desactivar_renombrar_y_fusionar(pg):
    app = App()
    categorias = RepositorioCategoriasSQLite(app.productos._con)
    gestion = GestionarCategorias(categorias, app.productos, app.cola)
    registrar = RegistrarProducto(app.productos, cola=app.cola, repositorio_categorias=categorias)

    mascotas = gestion.crear("Mascotas")
    varios = gestion.crear("Varios")
    registrar.ejecutar("M1", "Collar", 3000, categoria_id=varios.id)
    assert app.sincronizar().fallo_en is None
    assert _uno(pg, "SELECT activa FROM pos.categoria WHERE nombre = 'Mascotas'") is True

    gestion.cambiar_estado(mascotas.id, False)
    gestion.renombrar(mascotas.id, "Mascotas y animales")
    assert app.sincronizar().fallo_en is None
    assert _uno(pg, "SELECT count(*) FROM pos.categoria WHERE nombre = 'Mascotas'") == 0
    assert (
        _uno(pg, "SELECT activa FROM pos.categoria WHERE nombre = 'Mascotas y animales'") is False
    )

    # Para fusionar hacia ella hay que reactivarla; el producto se mueve y el origen se borra.
    gestion.cambiar_estado(mascotas.id, True)
    gestion.fusionar(varios.id, mascotas.id)
    assert app.sincronizar().fallo_en is None
    assert _uno(pg, "SELECT count(*) FROM pos.categoria WHERE nombre = 'Varios'") == 0
    assert (
        _uno(
            pg,
            "SELECT c.nombre FROM pos.producto p JOIN pos.categoria c ON c.id = p.categoria_id "
            "WHERE p.codigo = 'M1'",
        )
        == "Mascotas y animales"
    )


def test_venta_lleva_nota_y_motivo_del_descuento(pg):
    app = App()
    app.sembrar("A1", "Barra de cereal", 1200, 10)
    app.abrir.ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    venta = app.venta.iniciar(usuario_id=1)
    app.venta.agregar_producto(venta, "A1", 2)
    venta.aplicar_descuento("A1", 400, "Cortesía")
    venta.nota = "Para regalo"
    app.venta.agregar_pago(venta, Pago(medio=MedioPago.EFECTIVO, monto=Dinero(2000)))
    app.venta.cerrar(venta)

    assert app.sincronizar().fallo_en is None
    assert _uno(pg, "SELECT nota FROM pos.venta") == "Para regalo"
    motivo, descuento = _fila(pg, "SELECT motivo_descuento, descuento_linea FROM pos.venta_detalle")
    assert (motivo, descuento) == ("Cortesía", Decimal("400.00"))


def test_lote_llega_con_su_codigo_impreso(pg):
    app = App()
    lotes = RepositorioLotesSQLite(app.productos._con)
    app.sembrar("P1", "Yogurt", 1500, 0, perecible=True, dias_aviso=7)
    IngresarStock(app.productos, app.existencias, lotes, cola=app.cola).ejecutar(
        "P1",
        10,
        "Compra",
        fecha_vencimiento=date.today() + timedelta(days=5),
        codigo_lote="LT-77",
    )
    assert app.sincronizar().fallo_en is None
    assert _uno(pg, "SELECT codigo_lote FROM pos.lote") == "LT-77"


def test_la_migracion_007_se_puede_aplicar_dos_veces(pg):
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migraciones"
        / "007_sincronizacion_pantallas.sql"
    ).read_text()
    pg.execute("SET search_path TO pos;")
    pg.execute(sql)  # ya estaba aplicada por la fixture: no debe fallar
    pg.execute("RESET search_path;")
