"""Lotes, FEFO y politica de descuento sugerido (HU-INV-02, HU-INV-03, HU-INV-06)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.dominio.errores import DatosProductoInvalidos, ReglaInventarioInvalida
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
    ("dias", "esperado"),
    [
        (-1, 0),  # vencido: no se rebaja, no debe venderse
        (0, 50),
        (7, 50),  # etapa final: 7 dias o menos
        (8, 20),
        (14, 20),  # primera etapa: dentro de 14 dias
        (15, 0),  # todavia lejos
    ],
)
def test_politica_de_descuento_en_dos_etapas(dias, esperado):
    assert PoliticaDescuento().porcentaje(dias) == esperado


def test_politica_propia_del_producto_usa_sus_etapas_y_completa_con_el_defecto():
    pan = PoliticaDescuento().con_ajustes(dias_1=3, dias_2=1)  # solo cambia los dias
    assert (pan.dias_inicial, pan.pct_inicial, pan.dias_final, pan.pct_final) == (3, 20, 1, 50)
    assert pan.porcentaje(3) == 20 and pan.porcentaje(1) == 50 and pan.porcentaje(4) == 0
    queso = PoliticaDescuento().con_ajustes(dias_1=30, pct_1=15, dias_2=10, pct_2=40)
    assert queso.porcentaje(25) == 15 and queso.porcentaje(10) == 40


@pytest.mark.parametrize(
    "ajustes",
    [
        {"dias_1": 7},  # la etapa final (7 por defecto) no queda antes de la primera
        {"pct_1": 0},
        {"pct_2": 101},
        {"dias_2": 0},
    ],
)
def test_politica_rechaza_etapas_incoherentes(ajustes):
    with pytest.raises(DatosProductoInvalidos):
        PoliticaDescuento().con_ajustes(**ajustes)


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
