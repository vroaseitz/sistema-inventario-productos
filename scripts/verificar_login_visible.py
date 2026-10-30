"""Comprueba que el cuadro de acceso SE VE (A-03). Pensado para correr en Windows.

Abre la aplicacion real con login y verifica, mientras el cuadro esta abierto, que el cuadro y
la ventana principal estan visibles (el fallo original era un cuadro asociado a una ventana
oculta: en Windows no se ve y queda todo en negro). Despues crea el administrador y entra.

Uso:  python scripts/verificar_login_visible.py        (sale con 0 si todo esta bien)
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ["POS_SQLITE_PATH"] = str(Path(tempfile.mkdtemp()) / "verificar.db")
os.environ.pop("SUPABASE_DB_URL", None)

from pos.interfaz import ventana_principal  # noqa: E402
from pos.interfaz.login import DialogoAcceso, pedir_acceso  # noqa: E402

resultados: dict[str, object] = {}


def _con_comprobacion(parent, accion, primer_uso):
    def comprobar() -> None:
        dialogo = next(w for w in parent.winfo_children() if isinstance(w, DialogoAcceso))
        parent.update()
        resultados["dialogo_visible"] = bool(dialogo.winfo_viewable())
        resultados["ventana_visible"] = bool(parent.winfo_viewable())
        resultados["dialogo_al_frente"] = dialogo.winfo_exists() == 1
        dialogo.nombre.set("admin")
        dialogo.clave.set("clave-verificacion-1")
        dialogo.confirmar()

    parent.after(300, comprobar)
    return pedir_acceso(parent, accion, primer_uso)


ventana_principal.pedir_acceso = _con_comprobacion
ventana = ventana_principal.construir_aplicacion(con_login=True)
resultados["entro"] = "admin" in ventana.title()
ventana.destroy()

ok = all(resultados.get(k) for k in ("dialogo_visible", "ventana_visible", "entro"))
print(("OK" if ok else "FALLA"), resultados)
raise SystemExit(0 if ok else 1)
