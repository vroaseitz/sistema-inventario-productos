"""Escenario con la app REAL (Tk) para F4 Clientes y F5 Compras, usando sus formularios.

Lo ejecuta `test_clientes_compras_gui.py` en un proceso aparte. Solo se reemplazan los messagebox.
"""

from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
os.environ["POS_SQLITE_PATH"] = str(Path(tempfile.mkdtemp()) / "cc.db")
os.environ["SUPABASE_DB_URL"] = ""

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


def boton(ventana: tk.Misc, texto: str) -> ttk.Button:
    pila = list(ventana.winfo_children())
    while pila:
        w = pila.pop()
        if isinstance(w, ttk.Button) and w.cget("text") == texto:
            return w
        pila.extend(w.winfo_children())
    raise AssertionError(f"no hay botón {texto!r}")


app = ventana_principal.construir_aplicacion()
app.update()

# ------------------------------------------------------------------ F4 Clientes ---------
app.ir_a("F4")
app.update()
cli = app._marcos["F4"]
cli._nuevo_cliente()
app.update()
dlg = ultimo_dialogo(cli)
entradas = [w for w in dlg.winfo_children() if isinstance(w, ttk.Entry)]
for entrada, texto in zip(
    entradas, ("Rosa Prueba", "+56 9 1111 1111", "rosa@ejemplo.cl", "Familia"), strict=True
):
    entrada.insert(0, texto)
boton(dlg, "Guardar cliente").invoke()
app.update()
filas = [cli._tabla_lista.item(i, "values") for i in cli._tabla_lista.get_children()]
verificar(any("Rosa Prueba" in str(f) for f in filas), "el cliente nuevo aparece en la lista")

# duplicado: no se crea dos veces
cli._nuevo_cliente()
app.update()
dlg = ultimo_dialogo(cli)
[w for w in dlg.winfo_children() if isinstance(w, ttk.Entry)][0].insert(0, "Rosa Prueba")
boton(dlg, "Guardar cliente").invoke()
app.update()
verificar(len(cli._tabla_lista.get_children()) == 1, "no se duplica el cliente")
dlg.destroy()

# modificar
cli._tabla_lista.selection_set(cli._tabla_lista.get_children()[0])
cli._modificar_cliente()
app.update()
dlg = ultimo_dialogo(cli)
tel = [w for w in dlg.winfo_children() if isinstance(w, ttk.Entry)][1]
tel.delete(0, "end")
tel.insert(0, "+56 9 2222 2222")
boton(dlg, "Guardar cliente").invoke()
app.update()
cliente = cli._repo.listar()[0]
verificar(cliente.telefono == "+56 9 2222 2222", "modificar guarda el teléfono nuevo")

# desactivar
cli._tabla_lista.selection_set(cli._tabla_lista.get_children()[0])
cli._cambiar_estado()
app.update()
verificar(not cli._repo.listar()[0].activo, "desactivar saca al cliente de los activos")

# ------------------------------------------------------------------ F5 Compras ----------
cat = app._marcos["F2"]
cat._registrar.ejecutar("PROV1", "Harina de almendras 500 g", 6990, categoria_id=1, costo=3000)
app.ir_a("F5")
app.update()
comp = app._marcos["F5"]
comp.nuevo_proveedor()
app.update()
dlg = ultimo_dialogo(comp)
entradas = [w for w in dlg.winfo_children() if isinstance(w, ttk.Entry)]
entradas[0].insert(0, "Distribuidora Sur")
entradas[1].insert(0, "ventas@distribuidora.cl")
boton(dlg, "Crear proveedor").invoke()
app.update()
verificar(comp._proveedor.get() == "Distribuidora Sur", "el proveedor nuevo queda elegido")
verificar(
    "Distribuidora Sur" in comp._proveedores_tabla.item("prov-Distribuidora Sur", "values"),
    "el proveedor nuevo aparece en la pestaña Proveedores",
)
verificar(comp._proveedores_tabla.selection() == ("prov-Distribuidora Sur",), "queda resaltado")
comp._numero.set("F-1001")
comp._l_codigo.set("PROV1")
comp._l_cantidad.set("10")
comp._l_costo.set("3.500")
comp._agregar_linea()
app.update()
verificar(len(comp._lineas) == 1, "la línea entra al detalle de la factura")
verificar(comp._total.get() == "Total: $41.650", f"total con IVA 19 % {comp._total.get()}")
comp._confirmar()
app.update()
facturas = comp._facturas.listar()
verificar(len(facturas) == 1 and facturas[0].total == 41650, "la factura queda registrada")
producto = comp._productos.obtener_por_codigo("PROV1")
verificar(producto.costo.neto.monto == 3500, "el costo del producto se actualiza")
existencia = cat._consultar.repositorio_existencias.obtener("PROV1")
verificar(existencia is not None and int(existencia.cantidad) == 10, "entran 10 unidades al stock")
verificar(len(comp._lista.get_children()) == 1, "la factura aparece en Facturas de compra")
verificar(len(comp._proveedores_tabla.get_children()) == 1, "el proveedor aparece en Proveedores")

# misma factura dos veces: se rechaza
comp._proveedor.set("Distribuidora Sur")
comp._numero.set("F-1001")
comp._l_codigo.set("PROV1")
comp._l_cantidad.set("1")
comp._l_costo.set("3.500")
comp._agregar_linea()
comp._confirmar()
app.update()
verificar(len(comp._facturas.listar()) == 1, "una factura repetida no se registra dos veces")
app.destroy()
print("ESCENARIO OK")
