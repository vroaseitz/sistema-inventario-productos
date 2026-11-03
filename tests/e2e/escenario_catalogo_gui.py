"""Escenario con la app REAL (Tk) para F2 Catalogo: ficha, historial y categorias (CA-16).

Lo ejecuta `test_catalogo_gui.py` en un proceso aparte. Solo se reemplazan los messagebox.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
os.environ["POS_SQLITE_PATH"] = str(Path(tempfile.mkdtemp()) / "catalogo.db")
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


app = ventana_principal.construir_aplicacion()
app.update()
app.ir_a("F2")
app.update()
cat = app._marcos["F2"]
verificar(type(cat).__name__ == "VentanaCatalogo", "F2 es el catalogo del prototipo")

# --- Nuevo producto desde la ficha, como lo haria una persona ---
cat.nuevo()
app.update()
v = cat.ficha.v
nombres = list(cat.ficha.categorias)
v["codigo"].set("7801234500011")
v["nombre"].set("Castaña de cajú 1 kilo")
v["categoria"].set(nombres[0])
v["costo"].set("14.000")
v["precio"].set("22.220")
app.update()
verificar(v["ganancia"].get() == "$8.220", "ganancia en vivo = precio − costo")
verificar(v["margen"].get() == "37,0%", "margen en vivo")
verificar(v["markup"].get() == "58,7%", "markup en vivo")
verificar(v["iva"].get() == "$3.548", "IVA 19 % incluido informativo")
v["minimo"].set("3")
cat._guardar_ficha(cat.ficha, False)
app.update()
verificar(cat.tabla.exists("7801234500011"), "el producto nuevo aparece en la lista")
verificar(
    cat.tabla.selection() == ("7801234500011",), "el producto nuevo queda elegido en la lista"
)
verificar(
    cat.tabla.set("7801234500011", "categoria") == nombres[0],
    "la lista muestra la categoría del producto nuevo",
)
verificar(
    cat._repo.obtener_por_codigo("7801234500011").stock_minimo == 3, "guarda existencia mínima"
)

# --- Cambio de precio con motivo y historial ---
cat.tabla.selection_set("7801234500011")
cat.modificar()
app.update()
v = cat.ficha.v
v["precio"].set("23.000")
v["motivo"].set("Ajuste por alza de costo")
cat._guardar_ficha(cat.ficha, True)
app.update()
registros = cat._historial.listar_por_producto("7801234500011")
verificar(
    len(registros) == 1 and registros[0].motivo == "Ajuste por alza de costo",
    "historial guarda el motivo",
)
cat.ver_historial("7801234500011")
app.update()
cat.historial_abierto.destroy()

# --- Filtros: costo dudoso queda en Revisar ---
cat.nuevo()
app.update()
v = cat.ficha.v
v["codigo"].set("MIEL1")
v["nombre"].set("Miel Quillay 1 K")
v["categoria"].set(nombres[0])
v["costo"].set("5")
v["precio"].set("11.990")
cat._guardar_ficha(cat.ficha, False)
app.update()
verificar(cat.tabla.set("MIEL1", "estado") == "Revisar", "costo 5 se marca Revisar")
cat._buscar.set("castana")
cat.refrescar()
verificar(cat.tabla.get_children() == ("7801234500011",), "buscar sin tilde encuentra «Castaña»")
cat.limpiar_filtros()

# --- Desactivar sale de la lista (Activos) ---
cat.tabla.selection_set("MIEL1")
cat.alternar_estado()
app.update()
verificar(not cat.tabla.exists("MIEL1"), "producto desactivado sale de la lista de activos")
cat._estado.set("Inactivos")
cat.refrescar()
verificar(cat.tabla.exists("MIEL1"), "y aparece en Inactivos")
cat.limpiar_filtros()

# --- Categorias: nueva, renombrar, fusionar ---
cat.seleccionar_pestana("Categorías")
cat.refrescar_categorias()
antes = len(cat.tabla_categorias.get_children())
cat.nueva_categoria()
app.update()
cat.dialogo.variables["nombre"].set("Mascotas")
cat.dialogo.confirmar()
app.update()
verificar(len(cat.tabla_categorias.get_children()) == antes + 1, "categoría nueva en la lista")
verificar(
    cat.tabla_categorias.set(cat.tabla_categorias.selection()[0], "nombre") == "Mascotas",
    "la categoría nueva queda elegida en la lista",
)
nueva = next(
    i
    for i in cat.tabla_categorias.get_children()
    if cat.tabla_categorias.set(i, "nombre") == "Mascotas"
)
cat.tabla_categorias.selection_set(nueva)
cat.renombrar_categoria()
app.update()
cat.dialogo.variables["nombre"].set("Mascotas y animales")
cat.dialogo.confirmar()
app.update()
verificar(cat.tabla_categorias.set(nueva, "nombre") == "Mascotas y animales", "renombrar")
cat.tabla_categorias.selection_set(nueva)
cat.fusionar_categoria()
app.update()
cat.dialogo.variables["destino"].set(nombres[0])
cat.dialogo.confirmar()
app.update()
verificar(not cat.tabla_categorias.exists(nueva), "fusionar elimina la categoría origen")
# --- F3 con la forma del prototipo: Existencias | Lotes y vencimientos | Alertas ---
app.ir_a("F3")
app.update()
inv = app._marcos["F3"]
titulos = [inv._pestanas.tab(t, "text") for t in inv._pestanas.tabs()]
verificar(
    titulos == ["Existencias", "Lotes y vencimientos", "Alertas"], f"pestañas de F3 {titulos}"
)
inv._panel_entrada.abrir_entrada()
inv._panel_entrada.abrir_merma()
inv.abrir_reporte()
inv.abrir_movimientos()
app.update()
verificar(
    all(
        w.winfo_viewable()
        for w in (
            inv._panel_entrada.dlg_entrada,
            inv._panel_entrada.dlg_merma,
            inv._ventana_reporte,
            inv._ventana_movimientos,
        )
    ),
    "los 4 modales de F3 se abren",
)
# --- Regresion del E2E manual: ingresar stock refresca la pestaña Existencias ---
inv._codigo.set("7801234500011")
inv._cantidad.set("12")
inv._registrar()
app.update()
fila = [inv.existencias._tabla.item(i, "values") for i in inv.existencias._tabla.get_children()]
verificar(
    any(v[0].startswith("Casta") and str(v[1]) == "12" for v in fila),
    f"tras ingresar stock, Existencias se actualiza {fila}",
)

# --- F4 a F7: pestañas del prototipo y barras de acciones ---
for clave, esperadas in (
    ("F4", ["Clientes", "Cuenta", "Estado de cuenta"]),
    ("F5", ["Facturas de compra", "Registrar factura", "Proveedores"]),
    ("F6", ["Ventas", "Rentabilidad", "Rotación"]),
    ("F7", ["Usuarios", "Auditoría", "Configuración"]),
):
    app.ir_a(clave)
    app.update()
    marco = app._marcos[clave]
    nb = marco._pestanas
    titulos = [nb.tab(t, "text") for t in nb.tabs()]
    verificar(all(e in titulos for e in esperadas), f"{clave}: pestañas {titulos}")
app.destroy()
print("ESCENARIO OK")
