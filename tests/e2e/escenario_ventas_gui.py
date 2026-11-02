"""Escenario con la pantalla F1 real (Tk) para O-25, O-30 y O-02b.

Lo ejecuta `test_ventas_gui.py` en un proceso aparte (una sola ventana Tk por proceso). Sale con
codigo distinto de 0 si algo falla. Solo se reemplazan los cuadros modales (messagebox y el
conteo de billetes).
"""

from __future__ import annotations

import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from tkinter import Tk, Toplevel, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja  # noqa: E402
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja  # noqa: E402
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja  # noqa: E402
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta  # noqa: E402
from pos.dominio.inventario import Existencia  # noqa: E402
from pos.dominio.pagos import ConteoDenominaciones  # noqa: E402
from pos.dominio.productos import Producto, UnidadVenta  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_existencias import (  # noqa: E402
    RepositorioExistenciasSQLite,
)
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_tickets_espera import (  # noqa: E402
    RepositorioTicketsEsperaSQLite,
)
from pos.infraestructura.sqlite.repositorio_turnos_caja import (  # noqa: E402
    RepositorioTurnosCajaSQLite,
)
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite  # noqa: E402
from pos.interfaz import app_ventas  # noqa: E402

mensajes: list[tuple[str, str]] = []
respuestas = {"askyesno": True}
for _nombre in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, _nombre, lambda t, m, _n=_nombre, **k: mensajes.append((_n, m)))
messagebox.askyesno = lambda titulo, texto, **k: (
    mensajes.append(("askyesno", texto)) or respuestas["askyesno"]
)
app_ventas.VentanaVentas._contar_denominaciones_ui = lambda self, titulo: ConteoDenominaciones(
    {10000: 1}
)

raiz = Tk()
ruta = str(Path(tempfile.mkdtemp()) / "ventas.db")


def verificar(condicion: bool, texto: str) -> None:
    if not condicion:
        print("FALLO:", texto)
        sys.exit(1)
    print("ok:", texto)


def construir() -> tuple:
    """Abre la pantalla F1 sobre la base del archivo, como al iniciar la aplicacion."""
    con = crear_conexion(ruta)
    crear_esquema(con)
    productos, existencias = RepositorioProductosSQLite(con), RepositorioExistenciasSQLite(con)
    turnos, ventas = RepositorioTurnosCajaSQLite(con), RepositorioVentasSQLite(con)
    auditoria = RepositorioAuditoriaSQLite(con)
    ventana = app_ventas.VentanaVentas(
        raiz,
        turnos,
        productos,
        ventas,
        RegistrarVenta(ventas, turnos, productos, existencias),
        AbrirTurnoCaja(turnos),
        CerrarTurnoCaja(turnos, ventas),
        RegistrarMovimientoCaja(turnos),
        repo_tickets=RepositorioTicketsEsperaSQLite(con),
        auditoria=auditoria,
    )
    ventana.pack(fill="both", expand=True)
    raiz.update()
    return ventana, productos, existencias, turnos, auditoria


def cerrar_con_la_x(ventana) -> None:
    ventana.destroy()  # la X: no se pregunta ni se guarda nada especial
    raiz.update()


def escribir_y_esperar(ventana, texto: str) -> None:
    """Teclea el codigo en la caja de codigo (sin Enter) y deja pasar el tiempo del escaneo."""
    ventana._entrada_codigo.delete(0, "end")
    ventana._entrada_codigo.insert(0, texto)
    ventana._al_escribir_codigo(type("E", (), {"keysym": texto[-1]})())
    fin = time.time() + 0.8
    while time.time() < fin:
        raiz.update()
        time.sleep(0.02)


# --- datos: dos productos por unidad (uno con codigo prefijo del otro) y uno a granel -------
ventana, productos, existencias, turnos, auditoria = construir()
for codigo, nombre, precio, unidad in (
    ("7801", "Barra de cereal", 1200, UnidadVenta.UNIDAD),
    ("78012", "Barra de avena", 1500, UnidadVenta.UNIDAD),
    ("NUE", "Nueces", 18000, UnidadVenta.GRANEL),
):
    productos.guardar(Producto(codigo, nombre, Dinero(precio), unidad, 1))
    existencias.guardar(Existencia(codigo, Decimal("50")))

ventana._abrir_turno_ui()
verificar(turnos.obtener_abierto() is not None, "turno abierto")

# --- O-02b: al escanear se agrega solo, con cantidad 1 --------------------------------------
escribir_y_esperar(ventana, "78012")
verificar(
    [(d.producto_codigo, d.cantidad) for d in ventana._venta.detalles] == [("78012", 1)],
    "O-02b: un codigo completo se agrega solo con cantidad 1",
)
escribir_y_esperar(ventana, "7801")
verificar(
    len(ventana._venta.detalles) == 1, "O-02b: un codigo que es comienzo de otro espera el Enter"
)
ventana._agregar_producto()  # Enter
verificar(len(ventana._venta.detalles) == 2, "O-02b: con Enter se agrega el codigo ambiguo")
escribir_y_esperar(ventana, "NOEXISTE")
verificar(len(ventana._venta.detalles) == 2, "O-02b: un codigo inexistente no agrega nada")


# --- O-02b: a granel se abre el cuadro del peso y muestra el importe ------------------------
def buscar(raiz_widget, clase):
    for hijo in raiz_widget.winfo_children():
        if isinstance(hijo, clase):
            return hijo
        encontrado = buscar(hijo, clase)
        if encontrado is not None:
            return encontrado
    return None


def todos(raiz_widget, clase, salida):
    for hijo in raiz_widget.winfo_children():
        if isinstance(hijo, clase):
            salida.append(hijo)
        todos(hijo, clase, salida)
    return salida


estado: dict[str, object] = {}


def teclear_peso() -> None:
    dialogo = next(w for w in ventana.winfo_children() if isinstance(w, Toplevel))
    entrada = buscar(dialogo, ttk.Entry)
    dialogo.update()
    entrada.insert(0, "0,350")
    entrada.focus_force()
    entrada.event_generate("<KeyRelease>", keysym="0")
    dialogo.update()
    etiquetas = [w.cget("text") for w in todos(dialogo, ttk.Label, [])]
    estado["importe"] = next(t for t in etiquetas if t.startswith("Importe"))
    dialogo.event_generate("<Return>")


ventana._entrada_codigo.delete(0, "end")
ventana._entrada_codigo.insert(0, "NUE")
ventana.after(100, teclear_peso)
ventana._agregar_producto()  # Enter sobre un producto a granel: pide el peso
verificar(
    estado.get("importe") == "Importe: $6.300", f"O-02b: el cuadro muestra el importe {estado}"
)
linea = next(d for d in ventana._venta.detalles if d.producto_codigo == "NUE")
verificar(linea.cantidad == Decimal("0.350"), "O-02b: la linea a granel lleva el peso pedido")

# Esc cancela y no agrega nada
antes = len(ventana._venta.detalles)
ventana._entrada_codigo.delete(0, "end")
ventana._entrada_codigo.insert(0, "NUE")
ventana.after(
    100,
    lambda: next(w for w in ventana.winfo_children() if isinstance(w, Toplevel)).event_generate(
        "<Escape>"
    ),
)
ventana._agregar_producto()
verificar(len(ventana._venta.detalles) == antes, "O-02b/O-29: Esc cancela el peso y no agrega")

# --- O-25: dos tickets con productos sobreviven a cerrar con la X ----------------------------
ventana._nuevo_ticket()
escribir_y_esperar(ventana, "78012")
ventana._nuevo_ticket()  # un tercer ticket, vacio: no se guarda
verificar(len(ventana._tickets) == 3, "tres tickets abiertos")
textos = [ventana._nb_tickets.tab(i, "text") for i in range(3)]
verificar(
    textos[0].startswith("Ticket 1 · $") and textos[1].startswith("Ticket 2 · $"),
    f"pestanas con total {textos}",
)
verificar(textos[2] == "Ticket 3", "la pestana vacia no muestra total")
total1 = ventana._tickets[0].total.monto
total2 = ventana._tickets[1].total.monto

cerrar_con_la_x(ventana)
ventana, productos, existencias, turnos, auditoria = construir()  # se vuelve a abrir la app
verificar(
    len(ventana._tickets) == 2, f"O-25: vuelven 2 tickets al reabrir ({len(ventana._tickets)})"
)
verificar(
    [v.total.monto for v in ventana._tickets] == [total1, total2],
    "O-25: los tickets vuelven con sus productos",
)
cerrar_con_la_x(ventana)
ventana, productos, existencias, turnos, auditoria = construir()  # y otra vez
verificar(len(ventana._tickets) == 2, "O-25: siguen ahi tras reabrir por segunda vez")

# un ticket en espera no descuenta existencias
verificar(
    existencias.obtener("78012").cantidad == Decimal("50"), "el ticket en espera no descuenta stock"
)

# --- O-30: cerrar la jornada avisa, se puede volver o descartar -----------------------------
respuestas["askyesno"] = False
ventana._cerrar_turno_ui()
aviso = [m for tipo, m in mensajes if tipo == "askyesno"][-1]
verificar(
    "Quedan 2 tickets sin cobrar" in aviso and "$" in aviso,
    f"O-30: avisa cuantos y el total: {aviso!r}",
)
verificar(
    turnos.obtener_abierto() is not None and len(ventana._tickets) == 2,
    "O-30: «No» vuelve a los tickets",
)
verificar(auditoria.listar() == [], "O-30: no se registra nada si se vuelve")

respuestas["askyesno"] = True
ventana._cerrar_turno_ui()
verificar(turnos.obtener_abierto() is None, "O-30: confirmado, la jornada se cierra")
verificar(
    len(ventana._tickets) == 1 and ventana._tickets[0] is None, "O-30: los tickets se descartan"
)
registros = auditoria.listar("tickets_descartados_al_cerrar_jornada")
verificar(len(registros) == 1, "O-30: queda un registro en la auditoria")
detalle = registros[0]["detalle"]
verificar(
    detalle["cantidad"] == 2 and detalle["total"] == total1 + total2,
    f"auditoria: cantidad y total {detalle}",
)
verificar(
    len(detalle["tickets"]) == 2 and detalle["tickets"][0][0]["codigo"],
    "auditoria: guarda el contenido",
)
verificar(existencias.obtener("78012").cantidad == Decimal("50"), "descartar no ajusta existencias")
verificar(
    RepositorioTicketsEsperaSQLite(crear_conexion(ruta)).cargar() == [],
    "no quedan tickets guardados",
)

cerrar_con_la_x(ventana)
ventana, *_ = construir()
verificar(
    len(ventana._tickets) == 1 and ventana._tickets[0] is None,
    "al reabrir no vuelve nada descartado",
)

print("TODO OK")
raiz.destroy()
