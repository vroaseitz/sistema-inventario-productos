"""Pruebas de la entidad Producto y del value object Dinero."""

from decimal import Decimal

import pytest

from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero


def test_dinero_no_admite_negativos():
    with pytest.raises(DatosProductoInvalidos):
        Dinero(-100)


def test_dinero_suma():
    assert (Dinero(1000) + Dinero(500)).monto == 1500


def test_dinero_multiplicado():
    assert Dinero(1000).multiplicado_por(Decimal("2.5")).monto == 2500


def test_producto_requiere_codigo():
    with pytest.raises(DatosProductoInvalidos):
        Producto(codigo="", nombre="Arroz", precio=Dinero(1000))


def test_producto_requiere_nombre():
    with pytest.raises(DatosProductoInvalidos):
        Producto(codigo="123", nombre="  ", precio=Dinero(1000))


def test_producto_unidad_total_entero():
    p = Producto(codigo="1", nombre="Fideos", precio=Dinero(990), categoria_id=1)
    assert p.calcular_total(3).monto == 2970


def test_producto_unidad_rechaza_cantidad_fraccional():
    p = Producto(codigo="1", nombre="Fideos", precio=Dinero(990), categoria_id=1)
    with pytest.raises(DatosProductoInvalidos):
        p.calcular_total(Decimal("1.5"))


def test_producto_granel_cobra_por_kilo():
    p = Producto(
        codigo="12345",
        nombre="Nueces",
        precio=Dinero(8000),
        unidad_venta=UnidadVenta.GRANEL,
        categoria_id=1,
    )
    assert p.es_granel is True
    assert p.calcular_total(Decimal("1.500")).monto == 12000


def test_margen_y_markup_no_disponibles_sin_costo_cargado():
    # HU-PRD-03 / HU-PRD-08: sin costo cargado, los indicadores no estan disponibles.
    p = Producto(codigo="1", nombre="Miel", precio=Dinero(3000), categoria_id=1)
    assert p.margen is None
    assert p.markup is None


def test_margen_y_markup_se_calculan_sobre_el_neto():
    # Costo neto 1000, precio 2380 con IVA (neto 2000) -> margen 50% sobre venta, markup 100%.
    p = Producto(
        codigo="1",
        nombre="Miel",
        precio=Dinero(2380),
        categoria_id=1,
        costo=Costo(neto=Dinero(1000), iva=Dinero(190)),
    )
    assert p.margen == Decimal("0.5000")
    assert p.markup == Decimal("1.0000")


def test_markup_no_disponible_con_costo_neto_cero():
    # HU-PRD-08: costo neto realmente cero es distinto de costo no cargado,
    # pero el markup sobre cero sigue sin estar definido.
    p = Producto(
        codigo="1",
        nombre="Muestra gratis",
        precio=Dinero(500),
        categoria_id=1,
        costo=Costo(neto=Dinero(0), iva=Dinero(0)),
    )
    assert p.margen == Decimal("1.0000")
    assert p.markup is None


def test_neto_de_precio_quita_el_iva_con_redondeo_half_up():
    from pos.dominio.value_objects import neto_de_precio

    assert neto_de_precio(1190) == 1000
    assert neto_de_precio(4990) == 4193  # 4193.28
    assert neto_de_precio(1500) == 1261  # 1260.50 -> medio hacia arriba
    assert neto_de_precio(0) == 0


def test_el_margen_no_cuenta_el_iva_como_ganancia():
    # Caso real visto en la demo: precio 4.990 con IVA, costo neto 2.500.
    p = Producto(
        codigo="7801234567890",
        nombre="Miel de ulmo 500 g",
        precio=Dinero(4990),
        categoria_id=1,
        costo=Costo(neto=Dinero(2500), iva=Dinero(475)),
    )
    assert p.margen == Decimal("0.4038")  # (4193 - 2500) / 4193, no 49,9 %
