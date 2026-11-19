"""Migración de datos + correcciones del QA 18-11 sobre la app real (proceso aparte)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("tkinter")
pytest.importorskip("bcrypt")

SCRIPT = Path(__file__).with_name("escenario_migracion_y_qa_18_11_gui.py")
SIN_PANTALLA = (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")) or (
    sys.platform == "win32" and os.environ.get("SESSIONNAME") in (None, "", "Services")
)


@pytest.mark.skipif(SIN_PANTALLA, reason="sin entorno grafico")
def test_migracion_y_correcciones_qa_18_11():
    proceso = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, timeout=180
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
