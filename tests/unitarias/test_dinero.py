"""Pruebas de la politica de redondeo del value object Dinero (HALF_UP explicito)."""

from decimal import Decimal

from pos.dominio.value_objects import Dinero


def test_redondeo_half_up_en_multiplicacion():
    # 1 * 2.5 = 2.5 -> HALF_UP -> 3 (con redondeo medio-par daria 2).
    assert Dinero(1).multiplicado_por(Decimal("2.5")).monto == 3


def test_redondeo_half_up_desde_decimal():
    assert Dinero.desde_decimal(Decimal("2.5")).monto == 3
    assert Dinero.desde_decimal(Decimal("2.4")).monto == 2


def test_multiplicacion_exacta_sin_redondeo():
    assert Dinero(8000).multiplicado_por(Decimal("1.500")).monto == 12000


def test_medio_peso_sube():
    # 3 * 0.5 = 1.5 -> HALF_UP -> 2
    assert Dinero(3).multiplicado_por(Decimal("0.5")).monto == 2
