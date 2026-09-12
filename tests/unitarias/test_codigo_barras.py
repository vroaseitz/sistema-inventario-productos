"""Pruebas del parser de codigos de barras EAN-13 con peso/precio embebido."""

from decimal import Decimal

import pytest

from pos.dominio.codigo_barras import (
    TipoValorEmbebido,
    analizar_codigo,
    calcular_digito_verificador,
    es_codigo_interno,
    es_ean13_valido,
)
from pos.dominio.errores import CodigoBarrasInvalido


def ean13(doce: str) -> str:
    """Ayuda: arma un EAN-13 valido a partir de 12 digitos."""
    return doce + str(calcular_digito_verificador(doce))


# --- Digito verificador -------------------------------------------------------


def test_digito_verificador_caso_conocido():
    # 9780201379624 es un GTIN-13/ISBN valido conocido.
    assert calcular_digito_verificador("978020137962") == 4


def test_digito_verificador_requiere_12_digitos():
    with pytest.raises(CodigoBarrasInvalido):
        calcular_digito_verificador("123")


def test_ean13_valido_true():
    assert es_ean13_valido("9780201379624") is True


def test_ean13_valido_false_por_verificador():
    assert es_ean13_valido("9780201379625") is False


def test_ean13_valido_false_por_longitud():
    assert es_ean13_valido("123456") is False


def test_ean13_valido_false_por_no_numerico():
    assert es_ean13_valido("97802013796X") is False


# --- Clasificacion interno / normal ------------------------------------------


@pytest.mark.parametrize("prefijo", ["20", "21", "25", "29"])
def test_es_codigo_interno_true(prefijo):
    assert es_codigo_interno(prefijo + "00000000000") is True


@pytest.mark.parametrize("prefijo", ["19", "30", "78", "00"])
def test_es_codigo_interno_false(prefijo):
    assert es_codigo_interno(prefijo + "00000000000") is False


# --- Analisis de codigos normales --------------------------------------------


def test_analizar_codigo_normal_devuelve_codigo_completo():
    codigo = ean13("978020137962")
    lectura = analizar_codigo(codigo)
    assert lectura.es_interno is False
    assert lectura.es_granel is False
    assert lectura.codigo_producto == codigo
    assert lectura.peso_kg is None


# --- Analisis de codigos internos (granel) -----------------------------------


def test_analizar_codigo_interno_extrae_producto_y_peso():
    # prefijo 20 | producto 12345 | valor 01500 (=1500 g -> 1.500 kg)
    codigo = ean13("201234501500")
    lectura = analizar_codigo(codigo, tipo_valor=TipoValorEmbebido.PESO_GRAMOS)
    assert lectura.es_interno is True
    assert lectura.es_granel is True
    assert lectura.codigo_producto == "12345"
    assert lectura.peso_kg == Decimal("1.500")
    assert lectura.precio is None


def test_analizar_codigo_interno_como_precio():
    codigo = ean13("201234501500")
    lectura = analizar_codigo(codigo, tipo_valor=TipoValorEmbebido.PRECIO)
    assert lectura.precio == Decimal("1500")
    assert lectura.peso_kg is None


def test_analizar_codigo_interno_peso_cero():
    codigo = ean13("201234500000")
    lectura = analizar_codigo(codigo)
    assert lectura.peso_kg == Decimal("0.000")


# --- Errores -----------------------------------------------------------------


def test_analizar_codigo_longitud_invalida():
    with pytest.raises(CodigoBarrasInvalido):
        analizar_codigo("12345")


def test_analizar_codigo_verificador_invalido():
    with pytest.raises(CodigoBarrasInvalido):
        analizar_codigo("2012345015007")  # verificador casi seguro incorrecto


def test_analizar_codigo_no_numerico():
    with pytest.raises(CodigoBarrasInvalido):
        analizar_codigo("20123450150X0")
