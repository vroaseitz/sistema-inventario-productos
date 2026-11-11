"""QA 10-11: R-05 (reactivar en Rotacion), A-09 (columnas centradas) y A-10 (calendario)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("tkinter", reason="Tkinter no disponible en este entorno")

from pos.interfaz.app_reportes import VentanaReportes  # noqa: E402
from pos.interfaz.campo_fecha import CampoFecha  # noqa: E402
from pos.interfaz.tema import ancla_de_columna  # noqa: E402

# --- R-05 -----------------------------------------------------------------------------------


def _rotacion(estado: str) -> VentanaReportes:
    vista = VentanaReportes.__new__(VentanaReportes)
    vista._rot_estado = MagicMock(get=MagicMock(return_value=estado))
    vista._boton_reactivar = MagicMock(name="reactivar")
    vista._boton_desactivar = MagicMock(name="desactivar")
    return vista


def test_con_inactivos_reactivar_ocupa_el_lugar_de_desactivar():
    vista = _rotacion("Inactivos")
    vista._mostrar_boton_reactivar()
    vista._boton_reactivar.grid.assert_called_once()
    vista._boton_desactivar.grid_remove.assert_called_once()


@pytest.mark.parametrize("estado", ["Activos", "Todos"])
def test_sin_filtro_inactivos_se_ve_desactivar(estado):
    vista = _rotacion(estado)
    vista._mostrar_boton_reactivar()
    vista._boton_desactivar.grid.assert_called_once()
    vista._boton_reactivar.grid_remove.assert_called_once()


# --- A-09 -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "columna", ["producto", "nombre", "codigo", "categoria", "funcion", "Categoría", "Función"]
)
def test_nombre_codigo_categoria_y_funcion_quedan_a_la_izquierda(columna):
    assert ancla_de_columna(columna) == "w"


@pytest.mark.parametrize("columna", ["minimo", "ultima", "precio", "fecha", "estado", "saldo"])
def test_el_resto_de_los_datos_va_centrado(columna):
    assert ancla_de_columna(columna) == "center"


# --- A-10 -----------------------------------------------------------------------------------


def _campo_abierto(foco: str | None) -> CampoFecha:
    campo = CampoFecha.__new__(CampoFecha)
    popup = MagicMock(name="popup")
    popup.__str__ = MagicMock(return_value=".!campofecha.!toplevel")
    popup.focus_get.return_value = foco
    campo._popup = popup
    campo._cerrado_en = 0.0
    return campo


def test_clic_fuera_cierra_el_calendario():
    campo = _campo_abierto(".!ventana.!entry")
    campo._cerrar_si_perdio_foco()
    assert campo._popup is None


def test_foco_en_otra_aplicacion_cierra_el_calendario():
    campo = _campo_abierto(None)
    campo._cerrar_si_perdio_foco()
    assert campo._popup is None


def test_moverse_dentro_del_calendario_no_lo_cierra():
    campo = _campo_abierto(".!campofecha.!toplevel.!frame.!button")
    campo._cerrar_si_perdio_foco()
    assert campo._popup is not None


def test_si_el_campo_deja_de_verse_el_calendario_se_cierra():
    campo = _campo_abierto(".!campofecha.!toplevel")
    campo.winfo_viewable = MagicMock(return_value=0)  # otro modulo o pestana
    campo._vigilar_visibilidad()
    assert campo._popup is None
