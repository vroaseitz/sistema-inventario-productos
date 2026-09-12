"""Pruebas de la entidad Producto y del value object Dinero."""

from decimal import Decimal

import pytest

from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Dinero


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
    p = Producto(codigo="1", nombre="Fideos", precio=Dinero(990))
    assert p.calcular_total(3).monto == 2970


def test_producto_unidad_rechaza_cantidad_fraccional():
    p = Producto(codigo="1", nombre="Fideos", precio=Dinero(990))
    with pytest.raises(DatosProductoInvalidos):
        p.calcular_total(Decimal("1.5"))


def test_producto_granel_cobra_por_kilo():
    p = Producto(
        codigo="12345", nombre="Nueces", precio=Dinero(8000), unidad_venta=UnidadVenta.GRANEL
    )
    assert p.es_granel is True
    assert p.calcular_total(Decimal("1.500")).monto == 12000
