"""Pruebas de las reglas de inventario (Existencia)."""

from decimal import Decimal

import pytest

from pos.dominio.errores import ReglaInventarioInvalida
from pos.dominio.inventario import Existencia


def test_ingreso_suma_stock():
    e = Existencia("12345")
    e.ingresar(Decimal("10"))
    e.ingresar(Decimal("2.5"))
    assert e.cantidad == Decimal("12.5")


def test_descuento_resta_stock():
    e = Existencia("12345", Decimal("5"))
    e.descontar(Decimal("2"))
    assert e.cantidad == Decimal("3")


def test_no_permite_stock_negativo():
    e = Existencia("12345", Decimal("1"))
    with pytest.raises(ReglaInventarioInvalida):
        e.descontar(Decimal("2"))


def test_ingreso_debe_ser_positivo():
    e = Existencia("12345")
    with pytest.raises(ReglaInventarioInvalida):
        e.ingresar(Decimal("0"))


def test_stock_inicial_no_negativo():
    with pytest.raises(ReglaInventarioInvalida):
        Existencia("12345", Decimal("-1"))
