"""Formato y lectura de montos CLP (O-07): una sola funcion para toda la app."""

import pytest

from pos.dominio.errores import ReglaVentaInvalida
from pos.dominio.formato import formatear_clp, parsear_monto
from pos.dominio.pagos import calcular_cobro_efectivo
from pos.dominio.value_objects import Dinero


@pytest.mark.parametrize(
    ("monto", "texto"),
    [(0, "$0"), (990, "$990"), (15296, "$15.296"), (1234567, "$1.234.567"), (-5000, "-$5.000")],
)
def test_formatear_clp_con_punto_de_miles(monto, texto):
    assert formatear_clp(monto) == texto


@pytest.mark.parametrize("texto", ["5.000", "5000", "$5.000", " 5 000 "])
def test_parsear_monto_acepta_con_y_sin_punto(texto):
    assert parsear_monto(texto) == 5000


@pytest.mark.parametrize("texto", ["", "abc", "5,5"])
def test_parsear_monto_rechaza_lo_que_no_es_entero(texto):
    with pytest.raises(ValueError):
        parsear_monto(texto)


def test_los_mensajes_de_error_del_dominio_usan_punto_de_miles():
    with pytest.raises(ReglaVentaInvalida, match=r"\$15\.000.*\$15\.300"):
        calcular_cobro_efectivo(Dinero(15296), monto_entregado=Dinero(15000))


def test_formatear_cantidad_no_le_quita_ceros_a_los_enteros():
    from decimal import Decimal

    from pos.dominio.formato import formatear_cantidad

    assert formatear_cantidad(Decimal("30")) == "30"
    assert formatear_cantidad(Decimal("100")) == "100"
    assert formatear_cantidad(Decimal("10")) == "10"
    assert formatear_cantidad(Decimal("0")) == "0"
    assert formatear_cantidad(Decimal("2.500")) == "2,5"
    assert formatear_cantidad(Decimal("0.350")) == "0,35"
    assert formatear_cantidad(Decimal("29.650")) == "29,65"


def test_rango_de_busqueda_ordena_el_nombre_que_empieza_antes_que_una_palabra_que_empieza():
    from pos.dominio.formato import rango_de_busqueda

    assert rango_de_busqueda("Té verde hojas 100 g", "te") == 0  # el nombre empieza con «te»
    assert rango_de_busqueda("Barra de té", "te") == 1  # una palabra empieza con «te»
    assert rango_de_busqueda("Aceite de coco", "te") == 2  # solo lo contiene
    assert rango_de_busqueda("Miel", "te") == 3  # no coincide
    assert rango_de_busqueda("Cualquiera", "") == 0
    nombres = ["Aceite de coco", "Barra de té", "Té verde hojas 100 g", "Castaña de cajú"]
    ordenados = sorted(nombres, key=lambda n: (rango_de_busqueda(n, "TE"), n.lower()))
    assert ordenados[0] == "Té verde hojas 100 g"  # CA-15: sale primero
