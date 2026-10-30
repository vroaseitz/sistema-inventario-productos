"""Prueba de punta a punta con la APLICACION REAL (Tk) y PostgreSQL real.

Recorre lo que hace una persona: primer uso (crea administrador) -> reingreso con login ->
catalogo -> ingreso de stock con vencimiento (F3) -> abrir turno -> vender con el pago mixto ->
cerrar turno -> reporte (F6) -> sincronizar -> verificar en PostgreSQL.

Solo se reemplazan los cuadros de dialogo modales (messagebox y el conteo de billetes). Una
sola ventana por proceso (Tk 9 en macOS se cae al crear una segunda).

Requiere POS_TEST_PG_URL (ver test_sync_postgres.py); crea y borra el schema `pos` de esa base.
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("tkinter")
psycopg2 = pytest.importorskip("psycopg2")

PG_URL = os.environ.get("POS_TEST_PG_URL")
MIGRACIONES = Path(__file__).resolve().parents[2] / "database" / "migraciones"
SIN_PANTALLA = sys.platform.startswith("linux") and not os.environ.get("DISPLAY")

pytestmark = [
    pytest.mark.skipif(not PG_URL, reason="define POS_TEST_PG_URL"),
    pytest.mark.skipif(SIN_PANTALLA, reason="sin entorno grafico"),
]


def _migrar():
    if "supabase" in PG_URL.lower():
        pytest.fail("Este test BORRA el schema pos: nunca contra Supabase.")
    con = psycopg2.connect(PG_URL)
    con.autocommit = True
    cur = con.cursor()
    cur.execute("DROP SCHEMA IF EXISTS pos CASCADE; CREATE SCHEMA pos; SET search_path TO pos;")
    for migracion in sorted(MIGRACIONES.glob("[0-9]*.sql")):
        if not migracion.name.startswith("001"):
            cur.execute(migracion.read_text())
    cur.execute("RESET search_path;")
    return con, cur


def _rellenar_login(ventana, nombre, clave):
    """Escribe en el dialogo de acceso abierto y lo confirma (corre dentro de wait_window)."""
    from pos.interfaz.login import DialogoAcceso

    def accion():
        dialogo = next(w for w in ventana.winfo_children() if isinstance(w, DialogoAcceso))
        dialogo.nombre.set(nombre)
        dialogo.clave.set(clave)
        dialogo.confirmar()

    ventana.after(50, accion)


def test_flujo_completo_de_la_aplicacion(tmp_path, monkeypatch):
    from tkinter import messagebox

    from pos.dominio.pagos import ConteoDenominaciones
    from pos.interfaz import app_ventas, ventana_principal

    con_pg, cur = _migrar()
    mensajes = []
    for nombre in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(
            messagebox, nombre, lambda t, m, _n=nombre, **k: mensajes.append((_n, t, m))
        )
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setenv("POS_SQLITE_PATH", str(tmp_path / "pos.db"))
    # La app exige TLS por defecto (Supabase); el Postgres de pruebas local no lo tiene.
    monkeypatch.setenv("SUPABASE_DB_URL", PG_URL + "?sslmode=disable")
    monkeypatch.setattr(
        app_ventas.VentanaVentas,
        "_contar_denominaciones_ui",
        lambda self, titulo: ConteoDenominaciones({10000: 1, 1000: 5}),  # $15.000
    )
    clave = "clave-e2e-segura"

    # --- 1) primer uso: crea al administrador y entra --------------------------------------
    monkeypatch.setattr(
        ventana_principal,
        "pedir_acceso",
        lambda parent, accion, primer: _acceso_directo(parent, accion, primer, clave),
    )
    ventana = ventana_principal.construir_aplicacion(con_login=True)
    try:
        assert "admin" in ventana.title()
        ventas = ventana._marcos["F1"]
        inventario = ventana._marcos["F3"]
        reportes = ventana._marcos["F6"]
        assert ventas._sesion.usuario_id >= 1 and ventas._sesion.nombre == "admin"

        # --- 2) catalogo: dos productos (uno perecible) ------------------------------------
        from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto

        repo_productos = ventas._repo_productos
        registrar = RegistrarProducto(repo_productos, cola=ventas._cola)
        registrar.ejecutar("ARR", "Arroz 1 kg", 1500, categoria_id=1)
        registrar.ejecutar("CAF", "Cafe premium", 15296, categoria_id=1)
        registrar.ejecutar("YOG", "Yogurt", 2000, categoria_id=1, perecible=True, dias_aviso=7)

        # --- 3) F3: ingreso por la pantalla real; el perecible exige vencimiento -----------
        def ingresar(codigo, cantidad, vence=""):
            inventario._codigo.set(codigo)
            inventario._cantidad.set(cantidad)
            inventario._vence.set(vence)
            inventario._registrar()

        ingresar("ARR", "20")
        ingresar("CAF", "5")
        ingresar("YOG", "10")  # sin fecha: debe rechazarse
        assert mensajes[-1][0] == "showerror" and "vencimiento" in mensajes[-1][2].lower()
        ingresar("YOG", "10", (date.today() + timedelta(days=2)).isoformat())
        assert len(inventario._tabla.get_children()) == 1  # alerta con descuento sugerido
        assert "30%" in inventario._tabla.item(inventario._tabla.get_children()[0], "values")
        ingresar("YOG", "5", (date.today() + timedelta(days=5)).isoformat())  # segundo lote
        # I-02: la lista de lotes muestra ambos, el que vence antes primero
        filas = [
            inventario._tabla_lotes.item(f, "values")
            for f in inventario._tabla_lotes.get_children()
        ]
        assert [(f[1], str(f[3])) for f in filas] == [("Yogurt", "10"), ("Yogurt", "5")]
        assert filas[0][2] < filas[1][2]

        # --- 4) F1: abrir turno y vender (efectivo parcial + tarjeta) ----------------------
        ventas._abrir_turno_ui()
        assert "Turno #" in ventas._lbl_turno.cget("text")
        assert ventas._venta is not None  # D-01a: la venta queda lista

        def agregar(codigo, cantidad):
            ventas._entrada_codigo.insert(0, codigo)
            ventas._entrada_cantidad.delete(0, "end")
            ventas._entrada_cantidad.insert(0, cantidad)
            ventas._agregar_producto()

        agregar("ARR", "3")
        # O-04: con la linea seleccionada, "-" resta 1 (3 -> 2 = $3.000)
        ventas._tabla.selection_set(ventas._tabla.get_children()[0])
        ventas._ajustar_cantidad(-1)
        assert ventas._tabla.item(ventas._tabla.get_children()[0], "values")[2] == "2"
        agregar("YOG", "1")  # 2.000  -> total 5.000
        # I-03: la linea muestra el lote que vence antes (FEFO)...
        fila_yog = ventas._tabla.get_children()[1]
        assert (
            "vence " + (date.today() + timedelta(days=2)).isoformat()
            in ventas._tabla.item(fila_yog, "values")[5]
        )
        # ...y F5 "Cambiar lote" permite elegir el otro
        repo_lotes = ventas._registrar_venta.repositorio_lotes
        segundo = repo_lotes.por_producto("YOG")[1]
        ventas._registrar_venta.elegir_lote(ventas._venta, "YOG", segundo.uuid)
        ventas._refrescar_ticket()
        assert ventas._tabla.item(ventas._tabla.get_children()[1], "values")[5].startswith(
            f"* L{segundo.id}"
        )
        ventas._medio.set("efectivo")
        ventas._entrada_monto_pago.delete(0, "end")
        ventas._entrada_monto_pago.insert(0, "2000")  # efectivo PARCIAL
        ventas._agregar_pago()
        assert ventas._lista_pagos.size() == 1  # el parcial quedo registrado, sin vuelto
        ventas._medio.set("tarjeta")
        ventas._entrada_monto_pago.delete(0, "end")
        ventas._entrada_monto_pago.insert(0, "3000")
        ventas._agregar_pago()
        ventas._cerrar_venta()
        assert any("registrada con exito" in m[2] for m in mensajes)

        # --- 4b) O-27: con efectivo el total se ve redondeado desde el inicio ------------------
        assert [ventas._subpestanas.tab(i, "text") for i in (0, 1, 2)] == [
            "Venta",
            "Caja y corte",
            "Resumen del día",
        ]
        agregar("CAF", "1")  # $15.296 -> a la decena: $15.300
        assert ventas._lbl_a_cobrar.cget("text") == "A cobrar: $15.300"
        assert ventas._entrada_monto_pago.get() == "15300"
        ventas._entrada_monto_pago.delete(0, "end")
        ventas._entrada_monto_pago.insert(0, "15.300")  # con punto de miles tambien
        ventas._agregar_pago()
        ventas._cerrar_venta()
        assert "$32.300" in ventas._lbl_en_caja.cget("text")  # O-23: fondo 15.000 + 2.000 + 15.300

        # --- 4c) O-01b / O-25: varios tickets a la vez y ticket en espera que se conserva ---
        ventas._nuevo_ticket()
        assert len(ventas._tickets) == 2 and ventas._indice == 1
        agregar("ARR", "1")
        ventas._nb_tickets.select(0)
        ventas.update()
        assert ventas._indice == 0 and not ventas._venta.detalles  # el Ticket 1 sigue vacio
        ventas._nb_tickets.select(1)
        ventas.update()
        assert ventas._indice == 1 and ventas._venta.detalles  # el Ticket 2 sigue en espera
        guardados = ventas._repo_tickets.cargar()
        assert guardados == [{"productos": [["ARR", "1"]], "lotes": {}}]
        n_preguntas = len(mensajes)
        ventas._eliminar_ticket()  # tiene productos: pregunta (askyesno -> si)
        ventas._eliminar_ticket()  # el Ticket 1 vacio: ya no queda otro, se reinicia sin preguntar
        assert len(ventas._tickets) == 1 and ventas._repo_tickets.cargar() == []
        # al "reabrir" la aplicacion el ticket en espera vuelve con sus productos
        ventas._repo_tickets.guardar(guardados)
        ventas._restaurar_espera()
        assert [d.producto_codigo for d in ventas._venta.detalles] == ["ARR"]
        ventas._eliminar_ticket()
        assert len(mensajes) == n_preguntas

        # --- 5) stock descontado y FEFO sobre el lote ---------------------------------------
        assert str(ventas._registrar_venta.repositorio_existencias.obtener("ARR").cantidad) == "18"
        saldos = sorted(x.saldo for x in repo_lotes.por_producto("YOG"))
        assert [str(x) for x in saldos] == ["4", "10"]  # salio del lote elegido, no del FEFO

        # --- 6) cerrar turno con el arqueo ---------------------------------------------------
        ventas._cerrar_turno_ui()
        assert any(m[1] == "Arqueo de cierre" for m in mensajes)
        assert ventas._repo_turnos.obtener_abierto() is None

        # --- 6b) R-01: calendario desplegable en las fechas ---------------------------------
        campo = reportes._desde
        campo.abrir()
        assert campo.abierto
        campo._mover(-1)  # mes anterior
        campo._mover(1)
        campo._elegir(date.today())
        assert not campo.abierto and campo.get() == date.today().isoformat()
        inventario._vence.abrir()
        inventario._vence.cerrar()
        assert not inventario._vence.abierto

        # --- 7) reporte F6 ----------------------------------------------------------------------
        reportes.generar()
        assert "2 ventas" in reportes._resumen.get() and "$20.300" in reportes._resumen.get()

        # --- 8) sincronizar a PostgreSQL y verificar en el destino --------------------------
        assert len(ventas._cola.pendientes()) > 0
        ventas._sincronizar()
        assert ventas._cola.pendientes() == []
        cur.execute("SELECT count(*) FROM pos.venta")
        assert cur.fetchone()[0] == 2
        cur.execute("SELECT coalesce(sum(monto), 0) FROM pos.venta_pago")
        assert int(cur.fetchone()[0]) == 20300
        cur.execute("SELECT saldo FROM pos.lote ORDER BY saldo")
        assert [int(r[0]) for r in cur.fetchall()] == [4, 10]
        cur.execute("SELECT count(*) FROM pos.producto WHERE codigo IN ('ARR','YOG','CAF')")
        assert cur.fetchone()[0] == 3
    finally:
        ventana.destroy()
        cur.execute("DROP SCHEMA IF EXISTS pos CASCADE;")
        con_pg.close()


def _acceso_directo(parent, accion, primer_uso, clave):
    """Pasa por el dialogo real (DialogoAcceso) rellenandolo, como lo haria la persona."""
    from pos.interfaz.login import pedir_acceso

    assert primer_uso  # base nueva: pide crear el administrador
    parent.after(50, lambda: _llenar(parent, clave))
    return pedir_acceso(parent, accion, primer_uso)


def _llenar(parent, clave):
    from pos.interfaz.login import DialogoAcceso

    dialogo = next(w for w in parent.winfo_children() if isinstance(w, DialogoAcceso))
    dialogo.nombre.set("admin")
    dialogo.clave.set("corta")  # primero una clave invalida: no debe dejar entrar
    dialogo.confirmar()
    assert dialogo.winfo_exists() and dialogo.error.get()
    dialogo.clave.set(clave)
    dialogo.confirmar()
