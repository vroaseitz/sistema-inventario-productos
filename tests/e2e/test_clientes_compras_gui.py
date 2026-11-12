"""F4 Clientes y F5 Compras con la app real y sus formularios (proceso aparte)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("tkinter")
pytest.importorskip("bcrypt")

SCRIPT = Path(__file__).with_name("escenario_clientes_compras_gui.py")
SIN_PANTALLA = (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")) or (
    sys.platform == "win32" and os.environ.get("SESSIONNAME") in (None, "", "Services")
)


@pytest.mark.skipif(SIN_PANTALLA, reason="sin entorno grafico")
def test_clientes_y_compras_con_formularios_reales():
    proceso = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, timeout=120
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
