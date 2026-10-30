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
