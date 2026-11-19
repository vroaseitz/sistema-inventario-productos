"""CA-21: impuesto adicional a bebidas (IABA): se guarda aparte del neto y entra al margen."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto, costo_con_iaba
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_historial import RepositorioHistorialSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite


@pytest.fixture
def repo(tmp_path):
    con = crear_conexion(str(tmp_path / "i.db"))
    crear_esquema(con)
    return RepositorioProductosSQLite(con)


def test_el_iaba_se_calcula_aparte_del_neto():
    costo = costo_con_iaba(1000, 18)
    assert costo.neto.monto == 1000 and costo.impuesto_adicional.monto == 180
    assert costo.para_margen.monto == 1180
    assert costo_con_iaba(1000, None).impuesto_adicional.monto == 0


def test_el_margen_de_una_bebida_incluye_el_iaba_pero_no_el_iva():
    sin = Producto("B", "Bebida", Dinero(2380), categoria_id=1, costo=costo_con_iaba(1000, None))
    con = Producto(
        "B", "Bebida", Dinero(2380), categoria_id=1, costo=costo_con_iaba(1000, 18), iaba_pct=18
    )
    # precio sin IVA = 2000
    assert sin.margen == Decimal("0.5000")
    assert con.margen == Decimal("0.4100")  # (2000 - 1180) / 2000
    assert con.markup == Decimal("0.6949")  # (2000 - 1180) / 1180


def test_la_tasa_solo_puede_ser_10_o_18():
    with pytest.raises(DatosProductoInvalidos, match="10 % o 18 %"):
        Producto("B", "Bebida", Dinero(1000), categoria_id=1, iaba_pct=12)


def test_se_guarda_la_tasa_y_el_iaba_se_rearma_al_leer(repo):
    RegistrarProducto(repo).ejecutar("B", "Bebida", 2380, categoria_id=1, costo=1000, iaba_pct=10)
    leido = repo.obtener_por_codigo("B")
    assert leido.iaba_pct == 10
    assert leido.costo.neto.monto == 1000 and leido.costo.impuesto_adicional.monto == 100


def test_editar_la_tasa_recalcula_el_iaba_sobre_el_costo_que_ya_tenia(repo):
    RegistrarProducto(repo).ejecutar("B", "Bebida", 2380, categoria_id=1, costo=1000)
    editar = EditarProducto(repo, RepositorioHistorialSQLite(repo._con))
    editar.ejecutar("B", "Bebida", 2380, 1, "t", iaba_pct=18)  # sin tocar el costo
    assert repo.obtener_por_codigo("B").costo.impuesto_adicional.monto == 180
    editar.ejecutar("B", "Bebida", 2380, 1, "t", costo=2000, iaba_pct=18)
    assert repo.obtener_por_codigo("B").costo.impuesto_adicional.monto == 360
    editar.ejecutar("B", "Bebida", 2380, 1, "t")  # ya no esta afecto
    assert repo.obtener_por_codigo("B").costo.impuesto_adicional.monto == 0
    with pytest.raises(DatosProductoInvalidos):
        editar.ejecutar("B", "Bebida", 2380, 1, "t", iaba_pct=25)
