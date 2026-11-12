"""A-08: en el calendario, hoy y el dia elegido se resaltan con el color del modulo."""

from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("tkinter", reason="Tkinter no disponible en este entorno")

from pos.interfaz.campo_fecha import colores_del_dia  # noqa: E402
from pos.interfaz.tema import MODULOS_COLOR  # noqa: E402

HOY = date(2026, 11, 6)


def test_el_dia_elegido_va_relleno_con_el_color_del_modulo():
    colores = colores_del_dia(date(2026, 11, 10), date(2026, 11, 10), HOY, "F6")
    assert colores["bg"] == MODULOS_COLOR["F6"][0]
    assert colores["fg"] == "#ffffff"


def test_hoy_se_marca_con_el_color_del_modulo_y_borde():
    colores = colores_del_dia(HOY, date(2026, 11, 10), HOY, "F3")
    assert colores["fg"] == MODULOS_COLOR["F3"][0]
    assert colores["bg"] == MODULOS_COLOR["F3"][1]
    assert colores["relief"] == "solid"


def test_si_hoy_es_el_elegido_gana_el_relleno():
    colores = colores_del_dia(HOY, HOY, HOY, "F5")
    assert colores["bg"] == MODULOS_COLOR["F5"][0]


def test_un_dia_cualquiera_no_se_resalta():
    colores = colores_del_dia(date(2026, 11, 20), HOY, HOY, "F6")
    assert colores["bg"] not in {c for par in MODULOS_COLOR.values() for c in par}


def test_sin_modulo_usa_el_color_de_marca():
    colores = colores_del_dia(HOY, HOY, HOY, "")
    assert colores["fg"] == "#ffffff"
