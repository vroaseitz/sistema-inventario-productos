"""Escenario con la app REAL (Tk) para F2 Catalogo: ficha, historial y categorias (CA-16).

Lo ejecuta `test_catalogo_gui.py` en un proceso aparte. Solo se reemplazan los messagebox.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from tkinter import messagebox, ttk

sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows: cp1252 no codifica todo
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
os.environ["POS_SQLITE_PATH"] = str(Path(tempfile.mkdtemp()) / "catalogo.db")
os.environ["SUPABASE_DB_URL"] = ""

from pos.interfaz import ventana_principal  # noqa: E402
from pos.interfaz.combo_filtrable import ComboFiltrable  # noqa: E402

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

# --- R-03: al entrar a un campo con un numero, queda seleccionado y lo escrito lo reemplaza ---
campo_meta = ttk.Entry(app)
campo_meta.insert(0, "0")
campo_meta.pack()
campo_meta.event_generate("<FocusIn>")
app.update()
verificar(campo_meta.selection_present(), "R-03: el 0 queda seleccionado al entrar al campo")
campo_texto = ttk.Entry(app)
campo_texto.insert(0, "Nombre libre")
campo_texto.pack()
campo_texto.event_generate("<FocusIn>")
app.update()
verificar(not campo_texto.selection_present(), "R-03: un texto no se selecciona")
campo_meta.destroy()
campo_texto.destroy()

# --- CA-18: el desplegable de categoria deja escribir y filtra sin tildes ni mayusculas ---
combo = cat._combo_categoria
combo.focus_force()
combo.delete(0, "end")
combo.insert(0, "LACTEOS")
combo.event_generate("<KeyRelease>", keysym="S")
app.update()
verificar(
    list(combo.cget("values")) == ["Lácteos y huevos"], f"CA-18: filtra {combo.cget('values')}"
)
combo.event_generate("<Return>")
app.update()
verificar(cat._categoria.get() == "Lácteos y huevos", "CA-18: Enter elige la categoria filtrada")
combo.delete(0, "end")
combo.insert(0, "zzz inexistente")
combo.confirmar()
verificar(
    cat._categoria.get() == "Lácteos y huevos", "CA-18: lo escrito que no existe no se acepta"
)
combo.delete(0, "end")
combo.insert(0, "Todas")
combo.confirmar()
app.update()

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
verificar(v["ganancia"].get() == "$4.672", "ganancia en vivo = precio sin IVA − costo")
verificar(v["margen"].get() == "25,0%", "margen en vivo sobre el precio sin IVA")
verificar(v["markup"].get() == "33,4%", "markup en vivo")
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

# --- CA-19: el codigo de barras se puede cambiar desde la ficha ---
cat.tabla.selection_set("7801234500011")
cat.modificar()
app.update()
v = cat.ficha.v
mensajes.clear()
v["codigo"].set("MIEL1")  # ya existe (esta desactivado, pero existe)
verificar(
    cat._guardar_ficha(cat.ficha, True) is False
    and any("Ya existe un producto con código MIEL1" in m for _, m in mensajes),
    "CA-19: un codigo repetido se rechaza y la ficha queda abierta",
)
v["codigo"].set("7801234500099")
verificar(cat._guardar_ficha(cat.ficha, True) is True, "CA-19: el codigo nuevo se guarda")
app.update()
verificar(
    cat._repo.obtener_por_codigo("7801234500099") is not None
    and cat._repo.obtener_por_codigo("7801234500011") is None
    and cat.tabla.exists("7801234500099"),
    "CA-19: el producto pasa al codigo nuevo y la lista lo muestra",
)
verificar(
    any(
        f["accion"] == "Cambio de código de barras" and f["despues"] == "7801234500099"
        for f in cat._editar.auditor.repositorio.listar()
    ),
    "CA-19: el cambio queda en la auditoria",
)
cat.tabla.selection_set("7801234500099")  # y se devuelve, el resto del escenario usa el original
cat.modificar()
app.update()
cat.ficha.v["codigo"].set("7801234500011")
cat._guardar_ficha(cat.ficha, True)
app.update()
verificar(cat._repo.obtener_por_codigo("7801234500011") is not None, "CA-19: vuelve al original")

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
# --- CA-18 en «Fusionar»: el campo «Se queda en» deja escribir y filtra ---
for nombre_temporal in ("Temporal A", "Temporal B"):
    cat.nueva_categoria()
    app.update()
    cat.dialogo.variables["nombre"].set(nombre_temporal)
    cat.dialogo.confirmar()
    app.update()


def id_de(nombre_categoria):
    return next(
        i
        for i in cat.tabla_categorias.get_children()
        if cat.tabla_categorias.set(i, "nombre") == nombre_categoria
    )


cat.tabla_categorias.selection_set(id_de("Temporal A"))
cat.fusionar_categoria()
app.update()
combo_destino = next(w for w in cat.dialogo.winfo_children() if isinstance(w, ComboFiltrable))
cat.dialogo.focus_force()  # sin gestor de ventanas (CI) la tecla se pierde sin foco
cat.dialogo.update()
combo_destino.focus_force()
combo_destino.delete(0, "end")
combo_destino.insert(0, "LACTEOS")  # sin tilde y en mayusculas
combo_destino.event_generate("<KeyRelease>", keysym="S")
verificar(
    list(combo_destino.cget("values")) == ["Lácteos y huevos"],
    f"CA-18: «Se queda en» filtra lo escrito {combo_destino.cget('values')}",
)
cat.dialogo.confirmar()  # lo escrito se resuelve a la categoria completa antes de aceptar
app.update()
verificar(
    "Temporal A"
    not in [cat.tabla_categorias.set(i, "nombre") for i in cat.tabla_categorias.get_children()],
    "CA-18: fusionar con lo escrito funciona",
)

# --- CA-17: Eliminar solo si no tiene productos ---
mensajes.clear()
cat.tabla_categorias.selection_set(id_de(nombres[0]))  # tiene la castaña
cat.eliminar_categoria()
app.update()
verificar(
    any("producto" in m and "Fusionar" in m for _, m in mensajes)
    and nombres[0]
    in [cat.tabla_categorias.set(i, "nombre") for i in cat.tabla_categorias.get_children()],
    "CA-17: una categoria con productos no se elimina y pide fusionar",
)
cat.tabla_categorias.selection_set(id_de("Temporal B"))  # vacia
cat.eliminar_categoria()
app.update()
verificar(
    "Temporal B"
    not in [cat.tabla_categorias.set(i, "nombre") for i in cat.tabla_categorias.get_children()],
    "CA-17: una categoria vacia se elimina",
)

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
