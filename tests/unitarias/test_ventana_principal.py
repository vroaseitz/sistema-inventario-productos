"""Ventana unica F1-F7 (GEN-01). Las pruebas con Tk se omiten si no hay entorno grafico."""

import os
import re
import sys

import pytest

pytest.importorskip("tkinter")  # entornos sin Tk (p. ej. algunos Python de Homebrew)

from pos.interfaz.ventana_principal import MODULOS, construir_aplicacion  # noqa: E402


def test_hay_siete_modulos_con_atajo_y_color_del_prototipo():
    assert [m.clave for m in MODULOS] == [f"F{i}" for i in range(1, 8)]
    assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", m.color) for m in MODULOS)
    assert len({m.color for m in MODULOS}) == 7  # cada modulo con su franja


def test_solo_operacion_catalogo_e_inventario_se_declaran_implementados():
    # Honestidad: los demas modulos son marcadores, no pantallas (ver informe final).
    assert {m.clave for m in MODULOS if m.implementado} == {"F1", "F2", "F3"}


def _hay_pantalla() -> bool:
    # No se prueba abriendo un Tk de sondeo: Tk 9 en macOS se cae al crear un segundo Tk en el
    # mismo proceso. Por eso toda la verificacion grafica usa UNA sola ventana.
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY"))
    return True


@pytest.mark.skipif(not _hay_pantalla(), reason="sin entorno grafico")
def test_la_ventana_unica_monta_venta_y_productos_y_cambia_de_modulo(tmp_path, monkeypatch):
    monkeypatch.setenv("POS_SQLITE_PATH", str(tmp_path / "pos.db"))
    ventana = construir_aplicacion()  # no sincroniza: solo arma el publicador si hay URL
    try:
        assert type(ventana._marcos["F1"]).__name__ == "VentanaVentas"
        assert type(ventana._marcos["F2"]).__name__ == "VentanaProductos"
        assert ventana.modulo_activo == "F1"

        assert type(ventana._marcos["F3"]).__name__ == "VentanaInventario"
        ventana.mostrar("F3")
        assert ventana.modulo_activo == "F3"
        assert ventana._franja.cget("bg") == next(m.color for m in MODULOS if m.clave == "F3")
        ventana.mostrar("F99")  # clave inexistente: no cambia nada
        assert ventana.modulo_activo == "F3"

        for clave in ("F2", "F1", "F5", "F1"):  # ida y vuelta sin romper la pantalla de venta
            ventana.mostrar(clave)
            ventana.update()
        assert ventana.modulo_activo == "F1"
    finally:
        ventana.destroy()
