"""Escenario con la app REAL (Tk): anular una venta desde Caja y corte (HU-VTA-11).

Lo ejecuta `test_anular_venta_gui.py` en un proceso aparte. Solo se reemplazan los messagebox.
"""

from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox, ttk

sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows: cp1252 no codifica todo
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
os.environ["POS_SQLITE_PATH"] = str(Path(tempfile.mkdtemp()) / "anular.db")
os.environ["SUPABASE_DB_URL"] = ""

from pos.dominio.inventario import Existencia  # noqa: E402
from pos.dominio.pagos import MedioPago, Pago  # noqa: E402
from pos.dominio.productos import Producto  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.interfaz import ventana_principal  # noqa: E402

mensajes: list[tuple[str, str]] = []
for _n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, _n, lambda t, m, _x=_n, **k: mensajes.append((_x, m)))
messagebox.askyesno = lambda *a, **k: True


def verificar(condicion: bool, texto: str) -> None:
    if not condicion:
        print("FALLO:", texto, mensajes)
        sys.exit(1)
    print("ok:", texto)


def ultimo_dialogo(marco: tk.Misc) -> tk.Toplevel:
    return [w for w in marco.winfo_children() if isinstance(w, tk.Toplevel)][-1]


def boton(ventana: tk.Misc, texto: str):
    """Boton de la barra de acciones (BotonAccion) o ttk.Button con ese texto."""
    pila = list(ventana.winfo_children())
    while pila:
        w = pila.pop()
        if hasattr(w, "invoke") and getattr(w, "_etiqueta", None) is not None:
            if w._etiqueta.cget("text") == texto:
                return w
        elif isinstance(w, ttk.Button) and w.cget("text") == texto:
            return w
        pila.extend(w.winfo_children())
    raise AssertionError(f"no hay botón {texto!r}")


app = ventana_principal.construir_aplicacion()
app.update()
f1 = app._marcos["F1"]
productos, existencias = f1._repo_productos, f1._registrar_venta.repositorio_existencias
productos.guardar(Producto("ARR", "Arroz", Dinero(1000), categoria_id=1))
existencias.guardar(Existencia("ARR", Decimal("20")))

f1._abrir_turno.ejecutar(usuario_id=1, fondo_inicial=Dinero(10000))
f1._refrescar_turno()


def vender(cantidad: int):
    venta = f1._registrar_venta.iniciar(usuario_id=1)
    f1._registrar_venta.agregar_producto(venta, "ARR", cantidad)
    f1._registrar_venta.agregar_pago(venta, Pago(MedioPago.EFECTIVO, Dinero(venta.total.monto)))
    return f1._registrar_venta.cerrar(venta)


v1, v2 = vender(2), vender(3)  # $2.000 y $3.000; queda 15 en existencia
f1._refrescar_turno()
verificar(existencias.obtener("ARR").cantidad == Decimal("15"), "dos ventas descuentan 5")
# el boton existe en Caja y corte y abre el dialogo con las ventas cobradas
boton(f1, "Anular venta").invoke()
app.update()
dlg = ultimo_dialogo(f1)
tabla = next(w for w in dlg.winfo_children() if isinstance(w, ttk.Treeview))
numeros = [tabla.item(i, "values")[0] for i in tabla.get_children()]
verificar(numeros == [v2.id, v1.id] or numeros == [str(v2.id), str(v1.id)], f"lista {numeros}")
combo = next(w for w in dlg.winfo_children() if isinstance(w, ttk.Combobox))
verificar(
    list(combo.cget("values")) == ["Producto en mal estado", "Otro"],
    f"los motivos son los de la PO {combo.cget('values')}",
)
dlg.destroy()

# «Otro» sin explicar no se acepta; la venta queda como estaba
mensajes.clear()
verificar(f1.ejecutar_anulacion(v2.id, "Otro", "") is False, "«Otro» sin texto se rechaza")
verificar("escribe cuál" in mensajes[-1][1], f"aviso claro {mensajes[-1]}")

# anular de verdad
verificar(f1.ejecutar_anulacion(v2.id, "Otro", "Cobro equivocado") is True, "la venta se anula")
verificar(existencias.obtener("ARR").cantidad == Decimal("18"), "la existencia vuelve (15 + 3)")
filas = {i: f1._tabla_ventas_turno.item(i, "values") for i in f1._tabla_ventas_turno.get_children()}
anulada = filas[str(v2.id)]
verificar(
    anulada[4].startswith("Anulada") and "Cobro equivocado" in anulada[4],
    f"la venta anulada se ve marcada en la jornada {anulada}",
)
verificar(filas[str(v1.id)][4] == "Cobrada", "la otra sigue cobrada")
total = [f1._tabla_jornada.item(i, "values") for i in f1._tabla_jornada.get_children()]
verificar(("Total vendido", "$2.000") in total, f"el total vendido ya no la cuenta {total}")
verificar(
    ("Ventas anuladas (1)", "$3.000") in total,
    f"la anulacion es una partida propia del corte {total}",
)
verificar(
    "$12.000" in f1._lbl_en_caja.cget("text"), f"efectivo en caja {f1._lbl_en_caja.cget('text')}"
)

# una venta anulada no se anula de nuevo (y el dialogo ya no la ofrece)
mensajes.clear()
verificar(f1.ejecutar_anulacion(v2.id, "Producto en mal estado") is False, "no se anula dos veces")
verificar("ya está anulada" in mensajes[-1][1], f"aviso {mensajes[-1]}")
boton(f1, "Anular venta").invoke()
app.update()
tabla = next(w for w in ultimo_dialogo(f1).winfo_children() if isinstance(w, ttk.Treeview))
verificar(len(tabla.get_children()) == 1, "el dialogo solo ofrece la venta que sigue cobrada")
ultimo_dialogo(f1).destroy()

# queda en la auditoria (F7)
auditoria = f1._auditoria.listar(accion="Anulación de venta")
verificar(
    len(auditoria) == 1 and "Cobro equivocado" in auditoria[0]["despues"], f"auditoria {auditoria}"
)

# el cierre muestra la partida propia
mensajes.clear()
f1._contar_denominaciones_ui = lambda titulo: type("C", (), {"total": 12000})()
f1._cerrar_turno_ui()
arqueo = [m for t, m in mensajes if t == "showinfo"][-1]
verificar("Ventas anuladas: 1 por $3.000" in arqueo, f"el cierre la cuenta aparte {arqueo!r}")
verificar("Diferencia: $0" in arqueo, f"y el efectivo cuadra {arqueo!r}")
print("ok: escenario completo")
app.destroy()
