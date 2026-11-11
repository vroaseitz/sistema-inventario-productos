"""Escenario con la app REAL (Tk) para F7: usuarios, perfiles, cierre de sesion e inactividad.

Lo ejecuta `test_sesion_gui.py` en un proceso aparte. Solo se reemplazan los cuadros modales
(messagebox) y el cuadro de acceso se rellena solo, como lo haria una persona.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from tkinter import messagebox

sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows: cp1252 no codifica todo
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

os.environ["POS_SQLITE_PATH"] = str(Path(tempfile.mkdtemp()) / "sesion.db")
os.environ["SUPABASE_DB_URL"] = ""

from pos.interfaz import ventana_principal  # noqa: E402
from pos.interfaz.login import DialogoAcceso  # noqa: E402

mensajes: list[tuple[str, str]] = []
for _n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, _n, lambda t, m, _x=_n, **k: mensajes.append((_x, m)))
messagebox.askyesno = lambda *a, **k: True

pedir_real = ventana_principal.pedir_acceso
credenciales: list[tuple[str, str]] = []


def pedir_con_relleno(parent, accion, primer_uso):
    """Rellena el cuadro de acceso con la siguiente credencial de la lista."""
    nombre, clave = credenciales.pop(0)

    def rellenar() -> None:
        dialogo = next(w for w in parent.winfo_children() if isinstance(w, DialogoAcceso))
        dialogo.nombre.set(nombre)
        dialogo.clave.set(clave)
        dialogo.confirmar()

    parent.after(80, rellenar)
    return pedir_real(parent, accion, primer_uso)


ventana_principal.pedir_acceso = pedir_con_relleno


def verificar(condicion: bool, texto: str) -> None:
    if not condicion:
        print("FALLO:", texto)
        sys.exit(1)
    print("ok:", texto)


credenciales.append(("roxana", "clave-roxana-1"))  # primer uso: crea la administradora
app = ventana_principal.construir_aplicacion(con_login=True)
app.update()
verificar(app._lbl_usuario.cget("text") == "roxana · Administradora", "entra la administradora")
verificar(app._permitidos() == {"F1", "F2", "F3", "F4", "F5", "F6", "F7"}, "ve todos los modulos")

# --- F7: crear a la vendedora y probar las reglas ---------------------------------------------
f7 = app._marcos["F7"]
app.mostrar("F7")
app.update()
verificar(app.modulo_activo == "F7", "la administradora entra a F7")
mensajes.clear()
verificar(f7.crear_usuario("mostrador", "clave-1", "clave-1", "Vendedora") is False, "clave corta")
verificar("al menos 8" in mensajes[-1][1], f"mensaje de clave corta {mensajes[-1]}")
verificar(
    f7.crear_usuario("mostrador", "clave-mostrador-1", "otra-cosa-12", "Vendedora") is False,
    "no coinciden",
)
verificar(
    f7.crear_usuario("mostrador", "clave-mostrador-1", "clave-mostrador-1", "Vendedora"), "crea"
)
verificar(
    f7.crear_usuario("MOSTRADOR", "clave-mostrador-1", "clave-mostrador-1", "Vendedora") is False,
    "duplicado",
)
verificar(len(f7._tabla_usuarios.get_children()) == 2, "F7 lista a los 2 usuarios")
mensajes.clear()
verificar(f7.cambiar_estado("roxana") is False, "no se desactiva a si misma")
verificar(
    "tu propio usuario" in mensajes[-1][1] or "al menos una administradora" in mensajes[-1][1],
    "mensaje",
)
verificar(f7.cambiar_perfil("roxana", "Vendedora") is False, "no deja sin administradora")

# --- auditoria visible y configuracion --------------------------------------------------------
f7.refrescar()
operaciones = [f7._tabla_auditoria.item(i, "values")[2] for i in f7._tabla_auditoria.get_children()]
verificar("Alta de usuario" in operaciones, f"la auditoria muestra el alta {operaciones}")
f7._vars_config["fondo_habitual"].set("20.000")
verificar(f7.guardar_configuracion() is True, "guarda la configuracion")
verificar(f7._config.obtener("fondo_habitual") == 20000, "el fondo habitual quedo en $20.000")
f7._vars_config["aviso_defecto_dias"].set("0")
mensajes.clear()
verificar(
    f7.guardar_configuracion() is False and "entre 1 y 365" in mensajes[-1][1], "valida el rango"
)
f7._vars_config["aviso_defecto_dias"].set("7")
f7.guardar_configuracion()
cambios = [f for f in f7._auditoria.listar() if f["accion"] == "Cambio de configuración"]
verificar(
    any(c["antes"] == "$15.000" and c["despues"] == "$20.000" for c in cambios),
    "la auditoria guarda antes y despues de la configuracion",
)

# --- impresora: la prueba imprime (sin impresora configurada va a la carpeta «comprobantes») -----
f7._var_impresora.set("")
verificar(f7.imprimir_prueba() is True, "F7: imprimir prueba")
carpeta = Path(os.environ["POS_SQLITE_PATH"]).resolve().parent / "comprobantes"
pruebas = list(carpeta.glob("comprobante-*.txt"))
verificar(
    len(pruebas) == 1 and "PRUEBA DE IMPRESORA" in pruebas[0].read_text(encoding="utf-8"),
    "el ticket de prueba quedo en la carpeta",
)
f7._var_impresora.set("Xprinter_58")
f7.guardar_configuracion()
verificar(
    f7._config.obtener_texto("impresora_nombre") == "Xprinter_58",
    "guarda el nombre de la impresora",
)
cambios = [f for f in f7._auditoria.listar() if f["registro"] == "Impresora de comprobantes"]
verificar(
    bool(cambios) and cambios[0]["despues"] == "Xprinter_58",
    "la auditoria registra el cambio de impresora",
)
f7._var_impresora.set("")
f7.guardar_configuracion()

# --- cerrar sesion y entrar como vendedora ---------------------------------------------------
credenciales.append(("mostrador", "clave-mostrador-1"))
app._btn_salir.event_generate("<Button-1>")
app.update()
verificar(app._lbl_usuario.cget("text") == "mostrador · Vendedora", "entra la vendedora")
verificar(app._permitidos() == {"F1"}, "la vendedora solo ve F1")
verificar(app.modulo_activo == "F1", "queda en F1")
app.mostrar("F7")
app.mostrar("F2")
verificar(app.modulo_activo == "F1", "no puede entrar a F7 ni a F2")
verificar(
    str(app._pestanas["F7"].cget("fg")) == "#b5b9b8", "los modulos sin permiso se ven atenuados"
)

# --- cambiar mi contrasena --------------------------------------------------------------------
from pos.interfaz.acceso import dialogo_cambiar_clave  # noqa: E402

gestion = f7._gestion
dialogo = dialogo_cambiar_clave(app, "mostrador", gestion)
dialogo.variables["actual"].set("mala")
dialogo.variables["nueva"].set("clave-nueva-mostrador")
dialogo.variables["repetir"].set("clave-nueva-mostrador")
mensajes.clear()
dialogo.confirmar()
verificar("actual no es correcta" in mensajes[-1][1], "pide la clave actual correcta")
dialogo.variables["actual"].set("clave-mostrador-1")
dialogo.confirmar()
verificar(mensajes[-1] == ("showinfo", "Tu contraseña se cambió"), "cambia la contraseña")

# --- cierre por inactividad: sin tocar nada pide la clave de nuevo -------------------------
vencio: list[int] = []
# A-06: con cada_ms=10 s el cierre debe llegar cuando vence el plazo (0,6 s), no a los 10 s, y
# mover el mouse no debe reiniciar el conteo.
inicio = time.time()
app.vigilar_inactividad(lambda: 0.01, lambda: vencio.append(time.time() - inicio), cada_ms=10_000)
fin = time.time() + 3.0
while time.time() < fin and not vencio:
    app.event_generate("<Motion>", x=5, y=5)  # un roce del mouse cada 20 ms: no cuenta
    app.update()
    time.sleep(0.02)
verificar(bool(vencio), "la inactividad dispara el cierre de sesion")
verificar(
    vencio[0] < 1.5, f"A-06: cierra al vencer el plazo (0,6 s), no a los 10 s: {vencio[0]:.2f}"
)

# vuelve como administradora con la clave nueva de la vendedora no sirve y la vieja tampoco
credenciales.append(("roxana", "clave-roxana-1"))
app._btn_salir.event_generate("<Button-1>")
app.update()
verificar(
    app._permitidos() == {"F1", "F2", "F3", "F4", "F5", "F6", "F7"}, "vuelve la administradora"
)
auditoria = f7._auditoria.listar()
verificar(
    any(f["accion"] == "Cambio de contraseña" and f["usuario"] == "mostrador" for f in auditoria),
    "audita el cambio de clave",
)
print("TODO OK")
app.destroy()
