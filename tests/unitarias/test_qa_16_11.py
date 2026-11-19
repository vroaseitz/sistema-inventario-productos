"""QA 16-11: O-41 (Ir a la venta), A-11 (Insert), O-40 (cortes anteriores), O-42 (descuento
sugerido al vender) y CL-06 (saldo a favor)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

pytest.importorskip("tkinter", reason="Tkinter no disponible en este entorno")

from pos.dominio.caja import TurnoCaja  # noqa: E402
from pos.dominio.lotes import Lote, PoliticaDescuento  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_turnos_caja import (  # noqa: E402
    RepositorioTurnosCajaSQLite,
)
from pos.interfaz.app_clientes import _texto_deuda, _texto_disponible  # noqa: E402
from pos.interfaz.app_ventas import VentanaVentas  # noqa: E402
from pos.interfaz.cobro import MOTIVO_PROXIMO_A_VENCER, MOTIVOS_DESCUENTO  # noqa: E402
from pos.interfaz.ventana_principal import VentanaPrincipal  # noqa: E402

# --- O-41 -----------------------------------------------------------------------------------


def test_ir_a_la_venta_abre_la_pestana_venta_con_el_cursor_en_el_codigo():
    vista = VentanaVentas.__new__(VentanaVentas)
    vista._subpestanas = MagicMock()
    vista._entrada_codigo = MagicMock()
    vista.ir_a_la_venta()
    vista._subpestanas.select.assert_called_once_with(0)
    vista._entrada_codigo.focus_set.assert_called_once()


def test_la_tecla_del_modulo_actual_lo_lleva_a_su_pantalla_principal():
    ventana = VentanaPrincipal.__new__(VentanaPrincipal)
    f1 = MagicMock()
    ventana._activo = "F1"
    ventana._marcos = {"F1": f1}
    ventana.mostrar("F1")
    f1.al_repetir_tecla.assert_called_once()


# --- O-40 -----------------------------------------------------------------------------------


def test_jornadas_del_dia_devuelve_solo_las_de_esa_fecha():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    repo = RepositorioTurnosCajaSQLite(con)
    ayer = date.today() - timedelta(days=1)
    for dia in (ayer, ayer, date.today()):
        turno = TurnoCaja(1, Dinero(10000), abierto_en=datetime.combine(dia, datetime.min.time()))
        repo.guardar(turno)
        turno.cerrar(datetime.combine(dia, datetime.max.time()))
        repo.guardar(turno)
    jornadas = repo.jornadas_del_dia(ayer)
    assert [t.abierto_en.date() for t in jornadas] == [ayer, ayer]
    assert jornadas[0].id < jornadas[1].id
    assert repo.jornadas_del_dia(ayer - timedelta(days=5)) == []


# --- O-42 -----------------------------------------------------------------------------------


def _venta_con_lote(dias_para_vencer: int, dias_aviso: int = 30):
    vista = VentanaVentas.__new__(VentanaVentas)
    vista._tickets, vista._indice = [MagicMock()], 0  # `_venta` es el ticket activo
    lote = Lote("ALM", date.today() + timedelta(days=dias_para_vencer), Decimal("5"))
    vista._registrar_venta = MagicMock(lote_para=MagicMock(return_value=lote))
    producto = MagicMock(dias_aviso=dias_aviso, politica_descuento=lambda: PoliticaDescuento())
    vista._repo_productos = MagicMock(obtener_por_codigo=MagicMock(return_value=producto))
    vista._configuracion = None
    return vista, lote


@pytest.mark.parametrize(("dias", "porcentaje"), [(1, 50), (7, 50), (10, 20), (14, 20)])
def test_el_lote_por_vencer_sugiere_el_mismo_descuento_que_f3(dias, porcentaje):
    vista, lote = _venta_con_lote(dias)
    assert vista.descuento_sugerido("ALM") == (porcentaje, lote.fecha_vencimiento)


def test_un_lote_lejos_de_vencer_o_vencido_no_sugiere_descuento():
    assert _venta_con_lote(15)[0].descuento_sugerido("ALM") is None
    assert _venta_con_lote(60)[0].descuento_sugerido("ALM") is None
    assert _venta_con_lote(-1)[0].descuento_sugerido("ALM") is None


def test_proximo_a_vencer_es_un_motivo_de_descuento():
    assert MOTIVO_PROXIMO_A_VENCER in MOTIVOS_DESCUENTO


# --- CL-06 ----------------------------------------------------------------------------------


def test_saldo_negativo_se_muestra_a_favor():
    assert _texto_deuda(-390) == "A favor $390"
    assert _texto_deuda(1500) == "$1.500"


def test_el_disponible_aclara_que_incluye_el_saldo_a_favor():
    assert _texto_disponible(10000, -390) == "$10.390 (incl. a favor)"
    assert _texto_disponible(10000, 2000) == "$8.000"
    assert _texto_disponible(None, -390) == "—"


# --- CA-11 (regresion 17-11) -------------------------------------------------------------------


def test_la_ficha_nueva_abre_con_el_cursor_en_el_codigo():
    import tkinter as tk

    from pos.interfaz.app_catalogo import VentanaCatalogo

    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin entorno grafico")
    try:
        vista = VentanaCatalogo.__new__(VentanaCatalogo)
        tk.Frame.__init__(vista, raiz)
        vista.ficha = None
        vista._repo = MagicMock(obtener_por_codigo=MagicMock(return_value=None))
        vista._categorias_activas = lambda: {"Frutos secos": 1}
        vista._abrir_ficha(None)
        raiz.update()
        foco = str(raiz.tk.call("focus", "-lastfor", vista.ficha))
        assert foco.endswith("entry") and str(vista.ficha.v["codigo"]) == str(
            raiz.nametowidget(foco).cget("textvariable")
        )
    finally:
        raiz.destroy()
