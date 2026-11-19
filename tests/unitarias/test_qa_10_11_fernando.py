"""QA 10-11 (asignados a Fernando, hechos por Eduardo): CO-08 e I-07."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

pytest.importorskip("tkinter", reason="Tkinter no disponible en este entorno")

from pos.dominio.productos import Producto, UnidadVenta  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.interfaz.app_inventario import texto_cantidad_lote  # noqa: E402
from pos.interfaz.avisos import (  # noqa: E402
    costo_bajo_el_precio_o_confirmado,
    margen_negativo,
)

# --- CO-08 ----------------------------------------------------------------------------------


def test_almendras_a_5000_con_precio_3990_es_margen_negativo():
    """El caso del QA: ganancia -$1.647 (3.990 sin IVA = 3.353)."""
    assert margen_negativo(5000, 3990)


def test_costo_bajo_el_precio_con_iva_pero_sobre_el_neto_tambien_avisa():
    """$3.990 con costo $3.500: el aviso antiguo de F2 no saltaba y el margen es -$147."""
    assert margen_negativo(3500, 3990)


@pytest.mark.parametrize("costo", [None, 0, 3000, 3353])
def test_costo_normal_o_sin_costo_no_avisa(costo):
    assert not margen_negativo(costo, 3990)


def test_con_margen_negativo_pide_confirmacion_y_respeta_la_respuesta():
    with patch("pos.interfaz.avisos.messagebox.askyesno", return_value=False) as pregunta:
        assert not costo_bajo_el_precio_o_confirmado("Almendras", 5000, 3990)
    texto = pregunta.call_args.args[1]
    assert "El costo supera el precio de venta (margen negativo)" in texto
    assert "-$1.647" in texto


def test_sin_margen_negativo_no_pregunta():
    with patch("pos.interfaz.avisos.messagebox.askyesno") as pregunta:
        assert costo_bajo_el_precio_o_confirmado("Almendras", 3000, 3990)
    pregunta.assert_not_called()


# --- I-07 -----------------------------------------------------------------------------------


def _producto(unidad: UnidadVenta) -> Producto:
    return Producto("X", "X", Dinero(1000), unidad, categoria_id=1)


@pytest.mark.parametrize(
    ("cantidad", "esperado"),
    [("5.500", "5,5 kg"), ("14.500", "14,5 kg"), ("0.350", "0,35 kg"), ("32", "32 kg")],
)
def test_granel_se_muestra_en_kg_con_coma(cantidad, esperado):
    assert texto_cantidad_lote(Decimal(cantidad), _producto(UnidadVenta.GRANEL)) == esperado


def test_por_unidad_se_muestra_entero():
    assert texto_cantidad_lote(Decimal("12.000"), _producto(UnidadVenta.UNIDAD)) == "12"
