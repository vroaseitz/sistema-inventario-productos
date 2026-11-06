"""O-25, O-30 y O-02b con la pantalla F1 real. Corre en un proceso aparte (una ventana Tk)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("tkinter")

SCRIPT = Path(__file__).with_name("escenario_ventas_gui.py")
SIN_PANTALLA = (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")) or (
    sys.platform == "win32" and os.environ.get("SESSIONNAME") in (None, "", "Services")
)


@pytest.mark.skipif(SIN_PANTALLA, reason="sin entorno grafico")
def test_tickets_en_espera_cierre_de_jornada_y_escaneo():
    proceso = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, timeout=120
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
