"""MarcoDesplazable: lo que no cabe en la ventana se alcanza con scroll (Caja y corte).

Se ejecuta en un subproceso: el proyecto admite un unico `Tk()` por proceso (ver tests/e2e).
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("tkinter")

SIN_PANTALLA = (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")) or (
    sys.platform == "win32" and os.environ.get("SESSIONNAME") in (None, "", "Services")
)

SCRIPT = textwrap.dedent(
    """
    import sys, tkinter as tk
    from tkinter import ttk
    sys.path.insert(0, sys.argv[1])
    from pos.interfaz.desplazable import MarcoDesplazable

    raiz = tk.Tk()
    raiz.geometry("400x200")
    marco = MarcoDesplazable(raiz)
    marco.pack(fill="both", expand=True)
    for i in range(30):  # mucho mas alto que los 200 px de la ventana
        ttk.Label(marco.interior, text=f"fila {i}").pack()
    raiz.update()
    region = [int(v) for v in marco._lienzo.cget("scrollregion").split()]
    assert region[3] > marco._lienzo.winfo_height(), "el contenido deberia no caber"
    primero, ultimo = marco._lienzo.yview()
    assert primero == 0.0 and ultimo < 1.0, "solo debe verse el inicio"
    marco._lienzo.yview_moveto(1.0)
    assert marco._lienzo.yview()[1] == 1.0, "al bajar se debe llegar al final"
    assert marco.interior.winfo_width() >= marco._lienzo.winfo_width() - 2, "todo el ancho"
    raiz.destroy()
    print("ok")
    """
)


@pytest.mark.skipif(SIN_PANTALLA, reason="sin entorno grafico")
def test_el_contenido_alto_queda_alcanzable_por_scroll_y_ocupa_el_ancho():
    src = str(Path(__file__).resolve().parents[2] / "src")
    proceso = subprocess.run(
        [sys.executable, "-I", "-c", SCRIPT, src], capture_output=True, text=True, timeout=60
    )
    assert proceso.returncode == 0 and "ok" in proceso.stdout, proceso.stdout + proceso.stderr
