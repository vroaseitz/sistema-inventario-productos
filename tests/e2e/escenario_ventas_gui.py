"""Escenario con la pantalla F1 real (Tk) para O-25, O-30 y O-02b.

Lo ejecuta `test_ventas_gui.py` en un proceso aparte (una sola ventana Tk por proceso). Sale con
codigo distinto de 0 si algo falla. Solo se reemplazan los cuadros modales (messagebox y el
conteo de billetes).
"""

from __future__ import annotations

import sys
import tempfile
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import Tk, Toplevel, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja  # noqa: E402
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja  # noqa: E402
from pos.aplicacion.casos_uso.imprimir_comprobante import ImprimirComprobante  # noqa: E402
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja  # noqa: E402
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta  # noqa: E402
from pos.dominio.inventario import Existencia  # noqa: E402
from pos.dominio.pagos import ConteoDenominaciones  # noqa: E402
from pos.dominio.productos import Producto, UnidadVenta  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.infraestructura.impresion.impresoras import ImpresoraEnArchivo  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite  # noqa: E402
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
carpeta_comprobantes = Path(tempfile.mkdtemp())
impresora = ImpresoraEnArchivo(carpeta_comprobantes)


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
    clientes = RepositorioClientesSQLite(con)
    ventana = app_ventas.VentanaVentas(
        raiz,
        turnos,
        productos,
        ventas,
        RegistrarVenta(ventas, turnos, productos, existencias, repositorio_clientes=clientes),
        AbrirTurnoCaja(turnos),
        CerrarTurnoCaja(turnos, ventas, repositorio_clientes=clientes),
        RegistrarMovimientoCaja(turnos),
        repo_tickets=RepositorioTicketsEsperaSQLite(con),
        auditoria=auditoria,
        repo_clientes=clientes,
        imprimir=ImprimirComprobante(lambda: impresora, productos, ventas, cajera=lambda: "ana"),
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


# --- O-28 / O-07 / «Cambio»: F11 cambia el lote, monto con punto de miles, rotulos del prototipo --
ventana._abrir_turno_ui()
verificar(bool(raiz.bind("<F11>")), "O-28: F11 esta asignada a Cambiar lote")
verificar(not raiz.bind("<F5>"), "O-28: F5 ya no es de Cambiar lote (es el modulo Compras)")
escribir_y_esperar(ventana, "78012")
ventana._entrada_codigo.delete(0, "end")
verificar("Cambio:" in ventana._lbl_resumen.cget("text"), "la barra dice «Pagó con» y «Cambio»")
verificar(
    ventana._entrada_monto_pago.get() == "1.500", "O-07: el monto propuesto lleva punto de miles"
)

# --- I-03 / I-02 en F3 ---------------------------------------------------------------------
from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento  # noqa: E402
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock  # noqa: E402
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite  # noqa: E402
from pos.interfaz.app_inventario import VentanaInventario  # noqa: E402

con3 = crear_conexion(ruta)
lotes3 = RepositorioLotesSQLite(con3)
productos3 = RepositorioProductosSQLite(con3)
existencias3 = RepositorioExistenciasSQLite(con3)
from pos.aplicacion.casos_uso.registrar_merma import RegistrarMerma  # noqa: E402
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioAjustesSQLite  # noqa: E402

inventario = VentanaInventario(
    raiz,
    productos3,
    IngresarStock(productos3, existencias3, lotes3),
    ConsultarAlertasVencimiento(lotes3, productos3),
    lotes3,
    registrar_merma=RegistrarMerma(existencias3, RepositorioAjustesSQLite(con3), lotes3),
    repo_existencias=existencias3,
)
inventario.pack()
raiz.update()


def intentar(codigo, cantidad, vence="", codigo_lote=""):
    mensajes.clear()
    inventario._codigo.set(codigo)
    inventario._cantidad.set(cantidad)
    inventario._vence.set(vence)
    inventario._codigo_lote.set(codigo_lote)
    inventario._registrar()
    return [m for tipo, m in mensajes if tipo == "showerror"]


verificar(intentar("", "5") == ["Falta el código del producto"], "I-03: nombra el codigo faltante")
verificar(intentar("NUE", "") == ["Falta la cantidad"], "I-03: «Falta la cantidad»")
verificar(
    intentar("NUE", "abc") == ["La cantidad debe ser un número, por ejemplo 12"],
    "I-03: cantidad que no es numero",
)
verificar(intentar("NUE", "-2") == ["La cantidad debe ser mayor que cero"], "I-03: cantidad <= 0")
verificar(
    intentar("NUE", "5", "31/12/2030") == ["La fecha de vencimiento debe ser AAAA-MM-DD"],
    "I-03: fecha mal escrita",
)
verificar(intentar("NUE", "2", "2031-01-31", "L. 26089 A") == [], "ingreso valido sin errores")
verificar(
    [x.etiqueta for x in lotes3.por_producto("NUE")] == ["L. 26089 A"],
    "I-02: el lote lleva el codigo impreso",
)
filas = [
    inventario._tabla_lotes.item(i, "values")[0] for i in inventario._tabla_lotes.get_children()
]
verificar(filas == ["L. 26089 A"], f"I-02: F3 lista el lote por su codigo {filas}")


# --- HU-INV-04: registrar merma con motivo obligatorio --------------------------------------
def merma(codigo, cantidad, motivo=""):
    mensajes.clear()
    inventario._merma_codigo.set(codigo)
    inventario._merma_cantidad.set(cantidad)
    inventario._merma_motivo.set(motivo)
    inventario._registrar_merma()
    return [m for tipo, m in mensajes if tipo == "showerror"]


verificar(
    merma("NUE", "1") == ["Falta el motivo (es obligatorio)"], "HU-INV-04: el motivo es obligatorio"
)
verificar(
    merma("", "1", "Rotura") == ["Falta el código del producto"], "HU-INV-04: falta el codigo"
)
verificar(
    merma("NUE", "", "Rotura") == ["Falta la cantidad a dar de baja"],
    "HU-INV-04: falta la cantidad",
)
verificar(
    len(merma("NUE", "99", "Rotura")) == 1, "HU-INV-04: no se puede dar de baja mas de lo que hay"
)
inventario._merma_codigo.set("NUE")
inventario._merma_cantidad.set("0,5")
verificar(
    inventario._merma_estado.get() == "Existencia actual: 52  ·  Resultante: 51.5",
    f"HU-INV-04: muestra existencia actual y resultante ({inventario._merma_estado.get()})",
)
verificar(merma("NUE", "0,5", "Vencimiento") == [], "HU-INV-04: merma valida")
verificar(existencias3.obtener("NUE").cantidad == Decimal("51.5"), "HU-INV-04: baja el stock")
verificar(
    [x.saldo for x in lotes3.por_producto("NUE")] == [Decimal("1.5")],
    "HU-INV-04: baja tambien el lote",
)
inventario.destroy()

# --- R-02: F6 con nombres legibles y al mostrarse se regenera -------------------------------
from pos.aplicacion.casos_uso.reporte_ventas import ReporteVentas  # noqa: E402
from pos.infraestructura.sqlite.repositorio_categorias import (  # noqa: E402
    RepositorioCategoriasSQLite,
)
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite as RV  # noqa: E402
from pos.interfaz.app_reportes import VentanaReportes  # noqa: E402

reporte = VentanaReportes(
    raiz, ReporteVentas(RV(con3), productos3), RepositorioCategoriasSQLite(con3)
)
reporte.pack()
raiz.update()
ventana._agregar_pago()
ventana._cerrar_venta()  # una venta pagada con efectivo, despues de armar el reporte
reporte.al_mostrar()
categorias = [
    reporte._por_categoria.item(i, "values")[0] for i in reporte._por_categoria.get_children()
]
medios = [reporte._por_medio.item(i, "values")[0] for i in reporte._por_medio.get_children()]
verificar(categorias == ["Frutos secos y semillas"], f"R-02: categoria con su nombre {categorias}")
verificar(medios == ["Efectivo"], f"R-02: medio de pago legible {medios}")
verificar(
    "1 ventas" in reporte._resumen.get(), "R-02: al mostrarse el reporte ya trae la venta nueva"
)
reporte.destroy()

# --- F5 Compras: factura con detalle que actualiza costo y crea el lote ---------------------
from pos.aplicacion.casos_uso.registrar_factura_compra import RegistrarFacturaCompra  # noqa: E402
from pos.infraestructura.sqlite.repositorio_facturas_compra import (  # noqa: E402
    RepositorioFacturasCompraSQLite,
)
from pos.interfaz.app_compras import VentanaCompras  # noqa: E402

facturas = RepositorioFacturasCompraSQLite(con3)
compras = VentanaCompras(
    raiz,
    RegistrarFacturaCompra(facturas, productos3, existencias3, lotes3),
    facturas,
    productos3,
)
compras.pack()
raiz.update()


def linea(codigo, cantidad, costo, vence=""):
    mensajes.clear()
    compras._l_codigo.set(codigo)
    compras._l_cantidad.set(cantidad)
    compras._l_costo.set(costo)
    compras._l_vence.set(vence)
    compras._agregar_linea()
    return [m for tipo, m in mensajes if tipo == "showerror"]


verificar(linea("", "1", "1000") == ["Falta el código del producto"], "F5: falta el codigo")
verificar(len(linea("XXX", "1", "1000")) == 1, "F5: producto inexistente")
verificar(linea("7801", "", "1000") == ["Falta la cantidad"], "F5: falta la cantidad")
verificar(len(linea("7801", "10", "")) == 1, "F5: falta el costo")
verificar(linea("7801", "10", "1.000") == [], "F5: linea valida con punto de miles")
verificar(linea("NUE", "2,5", "11.765") == [], "F5: linea a granel con coma")
verificar(compras._neto.get() == "39.413", f"F5: el neto sigue a la suma {compras._neto.get()}")
verificar(compras._impuestos.get() == "7.488", f"F5: IVA 19 % {compras._impuestos.get()}")
verificar(compras._total.get() == "Total: $46.901", "F5: total neto + impuestos")
compras._proveedor.set("Distribuidora Andes")
compras._numero.set("F-4519")
compras._neto.set("39.000")
compras._al_editar_neto()
verificar(
    compras._diferencia.get() == "Diferencia con el neto: -$413",
    f"F5: muestra la diferencia {compras._diferencia.get()}",
)
mensajes.clear()
compras._confirmar()
verificar(
    any("debe ser cero" in m for tipo, m in mensajes if tipo == "showerror"),
    "F5: no confirma si el neto no coincide con el detalle",
)
verificar(facturas.listar() == [], "F5: nada se guardo")
compras._neto.set("39.413")
compras._al_editar_neto()
mensajes.clear()
compras._confirmar()
verificar(not [m for tipo, m in mensajes if tipo == "showerror"], f"F5: confirma {mensajes}")
verificar(len(facturas.listar()) == 1, "F5: la factura queda registrada")
verificar(productos3.obtener_por_codigo("7801").costo.neto.monto == 1000, "F5: actualiza el costo")
verificar(existencias3.obtener("7801").cantidad == Decimal("60"), "F5: ingresa el stock (50 + 10)")
verificar(len(compras._lista.get_children()) == 1, "F5: aparece en la lista de facturas")
compras.destroy()


# --- HU-VTA-06: cobrar e imprimir, cobrar solo registrando, reimprimir y corte ---------------
def vender_efectivo(imprimir):
    ventana._registrar_venta.agregar_producto(ventana._venta, "7801", 1)
    ventana._refrescar_ticket()
    ventana._medio.set("efectivo")
    ventana._entrada_monto_pago.delete(0, "end")
    ventana._entrada_monto_pago.insert(0, "1.200")
    ventana._agregar_pago()
    ventana._cerrar_venta(imprimir)


def comprobantes():
    return sorted(carpeta_comprobantes.glob("comprobante-*.txt"))


vender_efectivo(True)
verificar(len(comprobantes()) == 1, "HU-VTA-06: «Cobrar e imprimir ticket» imprime el comprobante")
texto = comprobantes()[0].read_text(encoding="utf-8")
verificar(
    "COMPROBANTE DE DETALLE" in texto and "Barra de cereal" in texto,
    "el comprobante lleva el detalle",
)
verificar("se abriria el cajon" in texto, "con efectivo se abre el cajon")
vender_efectivo(False)
verificar(len(comprobantes()) == 1, "HU-VTA-06: «Cobrar solo registrando» no imprime")
ventana._reimprimir_ultimo()
verificar(len(comprobantes()) == 2, "HU-VTA-06: «Reimprimir ultimo» (F8) imprime de nuevo")
verificar(
    "cajon" not in comprobantes()[-1].read_text(encoding="utf-8"), "la reimpresion no abre el cajon"
)
ventana._imprimir_corte()
verificar(
    "CORTE DE CAJA" in comprobantes()[-1].read_text(encoding="utf-8"),
    "HU-VTA-06: «Imprimir corte» imprime el corte de la jornada",
)
verificar(bool(raiz.bind("<F8>")), "F8 esta asignada a imprimir")

# --- F4 Clientes: cuenta de credito, venta a credito desde F1, abonos y cierre ---------------
from pos.aplicacion.casos_uso.gestionar_clientes import (  # noqa: E402
    GestionarClientes,
    RegistrarAbono,
)
from pos.interfaz.app_clientes import VentanaClientes  # noqa: E402

repo_cli = RepositorioClientesSQLite(con3)
f4 = VentanaClientes(
    raiz,
    GestionarClientes(repo_cli),
    RegistrarAbono(repo_cli, RepositorioTurnosCajaSQLite(con3)),
    repo_cli,
)
f4.pack()
raiz.update()


def errores():
    return [m for tipo, m in mensajes if tipo == "showerror"]


mensajes.clear()
verificar(f4.guardar_cliente(None, " ", "1", "", "") is False, "F4: rechaza sin nombre")
verificar(errores() == ["Falta el nombre del cliente"], f"F4: mensaje del nombre {errores()}")
mensajes.clear()
f4.guardar_cliente(None, "Cliente A", "", "", "")
verificar("medio de contacto" in errores()[0], "F4: exige un medio de contacto")
verificar(
    f4.guardar_cliente(None, "Cliente A", "+56 9 0000 0001", "", "") is True, "F4: crea cliente"
)
mensajes.clear()
f4.guardar_cliente(None, "cliente a", "2", "", "")
verificar("Ya existe" in errores()[0], "F4: no duplica el nombre")
cli_id = repo_cli.listar()[0].id
verificar(len(f4._tabla_lista.get_children()) == 1, "F4: el cliente aparece en la lista")

# Venta a credito desde F1: pide el cliente y carga la cuenta
ventana._elegir_cliente_ui = lambda: cli_id
ventana._registrar_venta.agregar_producto(ventana._venta, "7801", 1)
ventana._refrescar_ticket()
ventana._medio.set("credito_cliente")
ventana._entrada_monto_pago.delete(0, "end")
ventana._entrada_monto_pago.insert(0, "1.200")
ventana._agregar_pago()
verificar(ventana._venta.cliente_id == cli_id, "HU-CLI-02: la venta queda con el cliente elegido")
ventana._cerrar_venta()
verificar(sum(m.efecto for m in repo_cli.movimientos(cli_id)) == 1200, "HU-CLI-02: carga $1.200")
f4.mostrar_cuenta(cli_id)
filas = [f4._tabla_cuenta.item(i, "values") for i in f4._tabla_cuenta.get_children()]
verificar(filas[-1][1] == "Consumo" and filas[-1][3] == "$1.200", f"HU-CLI-03: la cuenta {filas}")
verificar("$1.200" in f4._lbl_saldo.cget("text"), "HU-CLI-03: saldo actual $1.200")

# Abonos: efectivo entra a la gaveta; el saldo no puede quedar negativo
mensajes.clear()
verificar(
    f4.registrar_abono(cli_id, "5.000", date.today().isoformat(), "Transferencia") is False,
    "abono > saldo",
)
verificar("supera el saldo" in errores()[0], f"HU-CLI-03: {errores()}")
verificar(
    f4.registrar_abono(cli_id, "500", date.today().isoformat(), "Efectivo") is True,
    "abono en efectivo",
)
verificar(
    "$700" in f4._lbl_saldo.cget("text"), f"HU-CLI-03: saldo $700 {f4._lbl_saldo.cget('text')}"
)
mensajes.clear()
ventana._cerrar_turno_ui()
arqueo = [m for tipo, m in mensajes if tipo == "showinfo"][-1]
verificar(
    "Abonos de clientes en efectivo: $500" in arqueo,
    f"HU-CAJ-03: el arqueo muestra el abono {arqueo!r}",
)
verificar("Crédito cliente: $1.200" in arqueo, "HU-CAJ-03: el credito va como partida aparte")

# Estado de cuenta y reporte de saldos
verificar(len(f4._tabla_estado.get_children()) == 1, "HU-CLI-04: el estado lista el consumo")
f4.refrescar()
saldos = [f4._tabla_saldos.item(i, "values") for i in f4._tabla_saldos.get_children()]
verificar(
    saldos[0][4] == "$700" and "$700" in f4._lbl_total_saldos.cget("text"), f"HU-CLI-05: {saldos}"
)

# Desactivar conserva el historial y saca al cliente de la lista de activos
f4.cambiar_estado(cli_id)
verificar(
    len(f4._tabla_lista.get_children()) == 0, "HU-CLI-01: inactivo sale de la lista de activos"
)
verificar(sum(m.efecto for m in repo_cli.movimientos(cli_id)) == 700, "el historial se conserva")
f4.destroy()

print("TODO OK")
raiz.destroy()
