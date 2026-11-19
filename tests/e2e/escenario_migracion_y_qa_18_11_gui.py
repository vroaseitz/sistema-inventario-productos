"""E2E con la app REAL (Tk): migracion de datos + correcciones del QA 18-11.

Lo ejecuta `test_migracion_y_qa_18_11_gui.py` en un proceso aparte. Usa CSV de ejemplo (sin datos
reales). Orden: migrar -> abrir la app -> vender a credito y con efectivo -> abono y estado de
cuenta (CL-08) -> anular con las tres opciones (CL-06) -> ficha de F2 (O-42, CA-21, CA-22) ->
cerrar la jornada sincronizando (SY-01, con un publicador falso: nunca se toca Supabase).
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox

sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows: cp1252 no codifica todo
sys.stderr.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))
CARPETA = Path(tempfile.mkdtemp())
os.environ["POS_SQLITE_PATH"] = str(CARPETA / "e2e.db")
os.environ["SUPABASE_DB_URL"] = ""

import importar_migracion  # noqa: E402

from pos.dominio.caja import calcular_arqueo  # noqa: E402
from pos.dominio.clientes import saldo_de  # noqa: E402
from pos.dominio.pagos import ConteoDenominaciones, MedioPago, Pago  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.dominio.ventas import DestinoDevolucion  # noqa: E402
from pos.interfaz import ventana_principal  # noqa: E402

mensajes: list[tuple[str, str]] = []
for _n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, _n, lambda t, m, _x=_n, **k: mensajes.append((_x, m)))
messagebox.askyesno = lambda *a, **k: True


def verificar(condicion: bool, texto: str) -> None:
    if not condicion:
        print("FALLO:", texto, mensajes[-3:])
        sys.exit(1)
    print("ok:", texto)


# ---------------------------------------------------------------- 1) migrar los CSV de ejemplo --
CAB_P = (
    "codigo;nombre;unidad_venta;categoria;origen_categoria;precio_venta_con_iva;costo_neto;iva;"
    "impuesto_adicional;costo_total_antiguo;existencia;stock_minimo;ultima_venta;en_los_1135;"
    "origen;observaciones"
)
FILAS_P = [
    "BEB1;Bebida cola 1,5 L;unidad;Líquidos;x;2380;1000;190;0;1190;24;;;si;ficha;",
    "PAN1;Pan amasado;unidad;Panadería y repostería;x;1500;600;114;0;714;10;;;si;ficha;",
    "GRA1;Almendras a granel;granel;Frutos secos y semillas;x;14990;8000;1520;0;9520;2,5;;;si;"
    "ficha;",
    "MER1;Mermelada artesanal;unidad;Aceites, untables y endulzantes;x;5565;2500;475;0;2975;10;;"
    ";si;ficha;",
    "FUDGE;;unidad;Sin categoría;x;990;;;;;0;;;no;sin ficha;",
    "7700000000001;;unidad;Líquidos;x;1000;500;95;0;595;1;;;si;ficha;",
]
CAB_C = "nombre;telefono;observaciones;cupo;deuda_actual;ultimo_pago"
FILAS_C = [
    "Cliente Credito;;vecino;50000;12000;2026-10-02",
    "Cliente Cero;;;20000;0;",
    ";;;1000;0;",
]


def csv(nombre: str, cabecera: str, filas: list[str]) -> Path:
    ruta = CARPETA / nombre
    ruta.write_bytes(("﻿" + "\r\n".join([cabecera, *filas]) + "\r\n").encode("utf-8"))
    return ruta


p, c = csv("p.csv", CAB_P, FILAS_P), csv("c.csv", CAB_C, FILAS_C)
salida = io.StringIO()
with redirect_stdout(salida):
    verificar_codigo = importar_migracion.main(["--productos", str(p), "--clientes", str(c)])
resumen = salida.getvalue()
verificar(verificar_codigo == 0, "el importador termina bien")
verificar(
    "5 leídos, 5 cargados, 0 ya existían, 1 rechazados" not in resumen, "resumen de productos"
)
verificar("Productos: 6 leídos, 5 cargados" in resumen, f"productos: 5 de 6 {resumen[:200]}")
verificar("Clientes: 3 leídos, 2 cargados" in resumen, "clientes: 2 de 3 (uno sin nombre)")
verificar(
    "Rechazado" in resumen and "7700000000001" in resumen, "se rechaza el sin nombre numerico"
)
salida2 = io.StringIO()
with redirect_stdout(salida2):
    importar_migracion.main(["--productos", str(p), "--clientes", str(c)])
verificar("0 cargados, 5 ya existían" in salida2.getvalue(), "idempotente: la 2.ª vez no duplica")

# --------------------------------------------------------------------------- 2) abrir la app --
app = ventana_principal.construir_aplicacion()
app.update()
f1, cli = app._marcos["F1"], app._marcos["F4"]
app.ir_a("F2")
app.update()
cat = app._marcos["F2"]
repo = f1._repo_productos
verificar(len(repo.listar()) == 5, "F2: los 5 productos migrados están en el catálogo")
verificar(repo.obtener_por_codigo("FUDGE").nombre == "FUDGE", "sin nombre pero código de texto")
verificar(
    repo.obtener_por_codigo("GRA1").es_granel
    and str(f1._registrar_venta.repositorio_existencias.obtener("GRA1").cantidad) == "2.5",
    "el granel migra en kg con decimales",
)
cargas = f1._registrar_venta.movimientos.repositorio.listar(codigo="BEB1")
verificar(
    [(str(m.cantidad), m.motivo) for m in cargas] == [("24", "Carga inicial")],
    "la existencia queda como «Carga inicial» en el historial",
)
clientes = {x.nombre: x for x in cli._repo.listar()}
verificar(set(clientes) == {"Cliente Credito", "Cliente Cero"}, "F4: los 2 clientes válidos")
credito, cero = clientes["Cliente Credito"], clientes["Cliente Cero"]
verificar(
    saldo_de(cli._repo.movimientos(credito.id)) == 12000, "su deuda entra como saldo anterior"
)
verificar(credito.cupo == 50000 and "Sin teléfono" in credito.telefono, "cupo y contacto pendiente")

# ----------------------------------------------------------------- 3) jornada y ventas (F1) --
f1._abrir_turno.ejecutar(usuario_id=1, fondo_inicial=Dinero(10000))
f1._refrescar_turno()


def vender(lineas, medio=MedioPago.EFECTIVO, cliente_id=None):
    venta = f1._registrar_venta.iniciar(usuario_id=1, cliente_id=cliente_id)
    for codigo, cantidad in lineas:
        f1._registrar_venta.agregar_producto(venta, codigo, cantidad)
    f1._registrar_venta.agregar_pago(venta, Pago(medio, Dinero(venta.total.monto)))
    return f1._registrar_venta.cerrar(venta)


credito_v = vender([("MER1", 2)], MedioPago.CREDITO_CLIENTE, credito.id)  # $11.130 a credito
verificar(credito_v.total.monto == 11130, "venta a crédito de un producto migrado: $11.130")
cli._abonar.ejecutar(credito.id, 5000, "transferencia")

# --------------------------------------------------------- 4) CL-08: estado de cuenta, 1 cifra --
cli.mostrar_cuenta(credito.id)
app.update()
r = cli._lbl_resumen
verificar(r["consumos"].cget("text") == "$11.130", "estado de cuenta: consumos $11.130")
verificar(r["descuento"].cget("text") == "− $2.226", "descuento del 20 %")
verificar(r["abonos"].cget("text") == "− $5.000", "abonos del ciclo")
verificar(
    r["falta"].cget("text") == "$3.904", f"CL-08: Falta pagar $3.904 {r['falta'].cget('text')}"
)
verificar(r["final"].cget("text") == "$18.130", "saldo final: 12.000 antiguos + 11.130 - 5.000")

# ------------------------------------------------------ 5) CL-06: anular con las tres opciones --
a_favor = vender([("PAN1", 2)], cliente_id=cero.id)  # $3.000 efectivo, con cliente
verificar(
    f1.ejecutar_anulacion(
        a_favor.id, "Producto en mal estado", "", DestinoDevolucion.SALDO_A_FAVOR
    ),
    "se anula dejando saldo a favor",
)
cli.mostrar_cuenta(cero.id)
app.update()
verificar(
    "A favor $3.000" in cli._lbl_saldo.cget("text"),
    f"F4 dice «A favor $3.000» {cli._lbl_saldo.cget('text')}",
)
devuelta = vender([("PAN1", 1)])  # $1.500 efectivo, sin cliente
verificar(
    f1.ejecutar_anulacion(devuelta.id, "Producto en mal estado", "", DestinoDevolucion.EFECTIVO),
    "se anula devolviendo en efectivo",
)
cambio = vender([("BEB1", 1)])  # $2.380 efectivo
verificar(
    f1.ejecutar_anulacion(cambio.id, "Producto en mal estado", "", DestinoDevolucion.CAMBIO),
    "se anula por cambio",
)
f1._abrir_venta_de_cambio(cambio.id)
verificar(
    f1._venta is not None and f1._venta.nota == f"Cambio de la venta N° {cambio.id}",
    "se abre la venta de cambio",
)
turno = f1._repo_turnos.obtener_abierto()
motivos = [m.motivo for m in turno.movimientos]
verificar(
    len(motivos) == 2 and all("Devolución" in m for m in motivos),
    f"dos retiros «Devolución»: {motivos}",
)
arqueo = calcular_arqueo(turno, f1._repo_ventas.obtener_por_turno(turno.id), Dinero(0))
verificar(
    arqueo.efectivo_esperado == 13000,
    f"arqueo sin doble descuento: 10.000 + 3.000 a favor = 13.000 ({arqueo.efectivo_esperado})",
)

# ------------------------------------------------- 6) F2: O-42, CA-21 y CA-22 sobre lo migrado --
cat._abrir_ficha("BEB1")
app.update()
v = cat.ficha.v
v["iaba"].set("18 %")
v["d1"].set("20")
v["p1"].set("30")
app.update()
verificar(
    v["iaba_monto"].get() == "$180" and v["margen"].get().startswith("41"), "CA-21: IABA y margen"
)
verificar(cat._guardar_ficha(cat.ficha, True) is True, "se guarda la ficha de un producto migrado")
beb = repo.obtener_por_codigo("BEB1")
verificar(
    beb.iaba_pct == 18 and beb.politica_descuento().porcentaje(20) == 30, "IABA y descuento propio"
)
cat._abrir_ficha("FUDGE")
cat._eliminar_producto(cat.ficha, "FUDGE")
verificar(repo.obtener_por_codigo("FUDGE") is None, "CA-22: se elimina el migrado sin historia")
cat._abrir_ficha("PAN1")
cat._eliminar_producto(cat.ficha, "PAN1")
pan = repo.obtener_por_codigo("PAN1")
verificar(pan is not None and not pan.activo, "CA-22: con ventas no se elimina, se desactiva")


# ----------------------------------------------------- 7) SY-01: cerrar la jornada sincronizando --
class Publicador:
    def __init__(self, falla: bool) -> None:
        self.falla, self.enviadas = falla, 0

    def publicar(self, operacion: dict) -> None:
        if self.falla:
            raise ConnectionError("sin internet")
        self.enviadas += 1


def contar(total: int) -> ConteoDenominaciones:
    return ConteoDenominaciones({10000: total // 10000, 1000: (total % 10000) // 1000})


pendientes = len(f1._cola.pendientes())
verificar(pendientes > 30, f"hay {pendientes} operaciones pendientes de la migración y las ventas")
f1._contar_denominaciones_ui = lambda *a, **k: contar(13000)
f1._publicador = Publicador(falla=True)
mensajes.clear()
f1._cerrar_turno_ui()
verificar(
    f1._repo_turnos.obtener_abierto() is None, "la jornada queda cerrada aunque no haya internet"
)
verificar(
    any("Quedan" in m[1] and "sin enviar" in m[1] for m in mensajes),
    "avisa cuántas quedan sin enviar",
)
verificar(len(f1._cola.pendientes()) >= pendientes, "todo sigue pendiente")
f1._abrir_turno.ejecutar(usuario_id=1, fondo_inicial=Dinero(10000))
f1._contar_denominaciones_ui = lambda *a, **k: contar(10000)
buena = Publicador(falla=False)
f1._publicador = buena
mensajes.clear()
f1._cerrar_turno_ui()
verificar(f1._repo_turnos.obtener_abierto() is None, "la 2.ª jornada también cierra")
verificar(
    any("Datos enviados a la nube" in m[1] for m in mensajes), "avisa «Datos enviados a la nube»"
)
verificar(
    f1._cola.pendientes() == [] and buena.enviadas > 30,
    f"la cola queda vacía ({buena.enviadas} enviadas)",
)
app.destroy()
print("ESCENARIO OK", date.today(), Decimal(0))
