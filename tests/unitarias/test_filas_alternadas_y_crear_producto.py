"""A-07 (filas alternadas en las tablas) y CO-01 (crear producto desde la factura de compra)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("tkinter", reason="Tkinter no disponible en este entorno")

from pos.interfaz.app_compras import VentanaCompras  # noqa: E402
from pos.interfaz.tema import etiquetas_de_fila  # noqa: E402

# --- A-07 -----------------------------------------------------------------------------------


def test_las_filas_pares_no_llevan_franja():
    assert etiquetas_de_fila(0, (), set()) == ()
    assert etiquetas_de_fila(2, ("inactivo",), set()) == ("inactivo",)


def test_las_filas_impares_llevan_franja():
    assert etiquetas_de_fila(1, (), set()) == ("fila_alterna",)
    assert etiquetas_de_fila(3, ("inactivo",), set()) == ("inactivo", "fila_alterna")


def test_una_fila_con_fondo_propio_conserva_su_aviso():
    """«revisar» (fondo rosado) no se tapa con la franja."""
    assert etiquetas_de_fila(1, ("revisar",), {"revisar"}) == ("revisar",)


# --- CO-01 ----------------------------------------------------------------------------------


def _compras(crear_producto=None) -> VentanaCompras:
    vista = VentanaCompras.__new__(VentanaCompras)
    vista._crear_producto = crear_producto
    vista._l_codigo = MagicMock(name="codigo")
    vista._mensaje = MagicMock(name="mensaje")
    vista._entrada_cantidad = MagicMock(name="entrada_cantidad")
    return vista


def test_codigo_nuevo_ofrece_crear_el_producto_con_el_codigo_escrito():
    crear = MagicMock(name="crear_producto")
    vista = _compras(crear)
    with patch("pos.interfaz.app_compras.messagebox.askyesno", return_value=True):
        vista._ofrecer_crear_producto("7801234567890")
    crear.assert_called_once_with("7801234567890", vista._producto_creado)


def test_si_no_quiere_crearlo_no_abre_la_ficha():
    crear = MagicMock(name="crear_producto")
    vista = _compras(crear)
    with patch("pos.interfaz.app_compras.messagebox.askyesno", return_value=False):
        vista._ofrecer_crear_producto("7801234567890")
    crear.assert_not_called()


def test_sin_acceso_a_f2_avisa_como_antes():
    vista = _compras(None)
    with patch("pos.interfaz.app_compras.messagebox.showerror") as error:
        vista._ofrecer_crear_producto("999")
    assert "No existe un producto con código 999" in error.call_args.args[1]


def test_al_guardar_la_ficha_vuelve_a_la_linea_de_la_factura():
    vista = _compras(MagicMock())
    vista._producto_creado("7801234567890")
    vista._l_codigo.set.assert_called_once_with("7801234567890")
    vista._entrada_cantidad.focus_set.assert_called_once()
    assert "7801234567890" in vista._mensaje.set.call_args.args[0]
