"""A-03: el cuadro de acceso debe verse. Se corre en un proceso aparte (una sola ventana Tk)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("tkinter")

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verificar_login_visible.py"
SIN_PANTALLA = (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")) or (
    # SSH en Windows corre en la sesion 0 (sin escritorio): las ventanas nunca quedan visibles.
    sys.platform == "win32" and os.environ.get("SESSIONNAME") in (None, "", "Services")
)


@pytest.mark.skipif(SIN_PANTALLA, reason="sin entorno grafico")
def test_el_cuadro_de_acceso_es_visible_y_permite_entrar():
    proceso = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, timeout=60
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
