"""F7 con la app real: usuarios, perfiles, cierre de sesion e inactividad (proceso aparte)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("tkinter")
pytest.importorskip("bcrypt")

SCRIPT = Path(__file__).with_name("escenario_sesion_gui.py")
SIN_PANTALLA = (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")) or (
    sys.platform == "win32" and os.environ.get("SESSIONNAME") in (None, "", "Services")
)


@pytest.mark.skipif(SIN_PANTALLA, reason="sin entorno grafico")
def test_usuarios_permisos_cierre_de_sesion_e_inactividad():
    proceso = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, timeout=120
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
