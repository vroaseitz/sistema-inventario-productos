"""Lotes, FEFO y politica de descuento sugerido (HU-INV-02, HU-INV-03, HU-INV-06)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.dominio.errores import ReglaInventarioInvalida
from pos.dominio.lotes import AlertaVencimiento, Lote, PoliticaDescuento, consumir_fefo
from pos.dominio.value_objects import Dinero

HOY = date(2026, 11, 2)


def _lote(dias: int, saldo: str = "10") -> Lote:
    return Lote("P1", HOY + timedelta(days=dias), Decimal(saldo))


def test_dias_para_vencer_y_vencido():
    assert _lote(5).dias_para_vencer(HOY) == 5
    assert _lote(-1).esta_vencido(HOY)
    assert not _lote(0).esta_vencido(HOY)  # vence hoy: aun se puede vender


def test_saldo_negativo_no_se_permite():
    with pytest.raises(ReglaInventarioInvalida):
        Lote("P1", HOY, Decimal("-1"))


def test_fefo_consume_primero_el_que_vence_antes():
    tarde, pronto = _lote(20, "10"), _lote(3, "10")
    sobrante = consumir_fefo([tarde, pronto], Decimal("12"))
    assert sobrante == 0
    assert pronto.saldo == 0 and tarde.saldo == 8


def test_fefo_devuelve_lo_que_no_cubren_los_lotes():
    # stock ingresado antes de que existieran los lotes: no se pierde, queda sin lote
    lote = _lote(3, "2")
    assert consumir_fefo([lote], Decimal("5")) == Decimal("3")
    assert lote.saldo == 0


def test_fefo_rechaza_cantidad_no_positiva():
    with pytest.raises(ReglaInventarioInvalida):
        consumir_fefo([_lote(3)], Decimal("0"))


@pytest.mark.parametrize(
    ("dias", "aviso", "esperado"),
    [
        (-1, 7, 0),  # vencido: no se rebaja, no debe venderse
        (0, 7, 30),
        (3, 7, 30),
        (4, 7, 20),
        (7, 7, 20),
        (8, 14, 10),  # dentro del aviso del producto, fuera de los tramos
        (15, 14, 0),  # todavia lejos
        (8, None, 0),  # sin aviso configurado
    ],
)
def test_politica_de_descuento_por_tramos(dias, aviso, esperado):
    assert PoliticaDescuento().porcentaje(dias, aviso) == esperado


def test_precio_sugerido_aplica_el_descuento_y_redondea_a_pesos():
    alerta = AlertaVencimiento(_lote(2), "Yogurt", Dinero(1990), 2, 30)
    assert alerta.precio_sugerido == Dinero(1393)  # 1990 * 0.70 = 1393
    sin_descuento = AlertaVencimiento(_lote(30), "Yogurt", Dinero(1990), 30, 0)
    assert sin_descuento.precio_sugerido == Dinero(1990)


def test_alerta_vencida_se_marca():
    assert AlertaVencimiento(_lote(-2), "x", Dinero(100), -2, 0).vencido


def test_proponer_lote_es_el_que_vence_antes_o_el_elegido():
    from pos.dominio.lotes import proponer_lote

    pronto, tarde, agotado = _lote(3), _lote(20), _lote(1, "0")
    assert proponer_lote([tarde, pronto, agotado]) is pronto  # FEFO, ignora el agotado
    assert proponer_lote([tarde, pronto], tarde.uuid) is tarde  # F5 Cambiar lote
    assert proponer_lote([agotado]) is None
    assert proponer_lote([tarde, pronto], "no-existe") is pronto


def test_fefo_consume_primero_el_lote_elegido():
    tarde, pronto = _lote(20, "10"), _lote(3, "10")
    assert consumir_fefo([tarde, pronto], Decimal("4"), tarde.uuid) == 0
    assert tarde.saldo == 6 and pronto.saldo == 10
