"""GUI de escritorio con Tkinter para venta y caja (HU-VTA-01/03/04, HU-CAJ-01/02/04).

Mismo criterio que app_tkinter.py: la ventana recibe los casos de uso ya armados
por constructor y solo orquesta la vista. Toda la logica de negocio (redondeo,
vuelto, arqueo, validaciones) vive en dominio/aplicacion y ya esta probada en
tests/unitarias/test_pagos.py, test_ventas.py, test_caja.py y
tests/integracion/test_ventas_caja_e2e.py.

Ajustado tras la ronda de QA del 26-10-2026 (Hallazgos-QA_NaturalSur.xlsx,
casos D-01 a F-04): venta siempre abierta, Enter en los campos clave, quitar
lineas y pagos antes de cobrar, validacion de stock y de pago al agregarlos
(no recien al cerrar), montos con separador de miles, y el numero grande es
lo que hay que cobrar, no el total sin redondear.
"""

from __future__ import annotations

import time
import tkinter as tk
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from tkinter import Listbox, Misc, StringVar, Toplevel, messagebox, ttk

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.anular_venta import AnularVenta
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
from pos.aplicacion.casos_uso.imprimir_comprobante import ImprimirComprobante
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.casos_uso.resumen_del_dia import ResumenDelDia
from pos.aplicacion.casos_uso.sincronizar_pendientes import SincronizarPendientes
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    PublicadorRemoto,
    RepositorioAuditoria,
    RepositorioCategorias,
    RepositorioClientes,
    RepositorioConfiguracion,
    RepositorioProductos,
    RepositorioTicketsEspera,
    RepositorioTurnosCaja,
    RepositorioVentas,
)
from pos.dominio.caja import TipoMovimientoCaja, calcular_arqueo
from pos.dominio.clientes import saldo_de
from pos.dominio.errores import ErrorDominio, ErrorImpresion
from pos.dominio.formato import (
    formatear_clp,
    formatear_fecha_corta,
    parsear_monto,
    rango_de_busqueda,
)
from pos.dominio.pagos import (
    DENOMINACIONES_CLP,
    ConteoDenominaciones,
    MedioPago,
    Pago,
    redondear_a_decena,
)
from pos.dominio.productos import UnidadVenta
from pos.dominio.usuarios import Rol
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import MOTIVO_OTRO, MOTIVOS_ANULACION, EstadoVenta, Venta
from pos.interfaz.cobro import DialogoCobro, DialogoDescuento, DialogoEspera
from pos.interfaz.desplazable import MarcoDesplazable
from pos.interfaz.dialogo_formulario import pedir_formulario
from pos.interfaz.panel_dia import PanelDelDia
from pos.interfaz.sesion import Sesion
from pos.interfaz.tema import (
    LINEA_2,
    MODULOS_COLOR,
    PAPEL,
    TINTA,
    TINTA_2,
    TINTA_3,
    BotonAccion,
    fuente,
)

SIN_CLIENTE = "— sin cliente —"
USUARIO_DEMO = 1  # usuario por defecto cuando no hay sesion (pruebas / sin login)

# Motivos validados por la Product Owner el 22-09 (HU-CAJ-04, hallazgo E-03).
MOTIVOS_MOVIMIENTO_CAJA = (
    "Ingreso de sencillo",
    "Retiro planificado para deposito bancario",
    "Retiro por resguardo durante la jornada",
)
# O-35 (Excel de hallazgos): cada tipo muestra solo sus motivos. Ingreso: solo «Ingreso de sencillo»
# (la PO confirmo el 09-11 que no tienen propinas); retiro: el deposito bancario y el resguardo.
MOTIVOS_POR_TIPO = {
    TipoMovimientoCaja.INGRESO: (MOTIVOS_MOVIMIENTO_CAJA[0],),
    TipoMovimientoCaja.RETIRO: (MOTIVOS_MOVIMIENTO_CAJA[1], MOTIVOS_MOVIMIENTO_CAJA[2]),
}

NOMBRES_MEDIO_PAGO = {
    MedioPago.EFECTIVO: "Efectivo",
    MedioPago.TARJETA: "Tarjeta",
    MedioPago.TRANSFERENCIA: "Transferencia",
    MedioPago.CREDITO_CLIENTE: "Crédito cliente",
}


_formatear_clp = formatear_clp  # funcion unica de formato (O-07)


def _normalizar(texto: str) -> str:
    """Minusculas y sin tildes, para buscar sin que el acento importe (D-26)."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.lower()


class VentanaVentas(ttk.Frame):
    """Pantalla de Venta y Caja (F1). Es un marco: la ventana la aporta VentanaPrincipal."""

    def __init__(
        self,
        parent: Misc,
        repositorio_turnos: RepositorioTurnosCaja,
        repositorio_productos: RepositorioProductos,
        repositorio_ventas: RepositorioVentas,
        registrar_venta: RegistrarVenta,
        abrir_turno: AbrirTurnoCaja,
        cerrar_turno: CerrarTurnoCaja,
        registrar_movimiento: RegistrarMovimientoCaja,
        cola: ColaSincronizacion | None = None,
        publicador: PublicadorRemoto | None = None,
        sesion: Sesion | None = None,
        repo_tickets: RepositorioTicketsEspera | None = None,
        auditoria: RepositorioAuditoria | None = None,
        repo_clientes: RepositorioClientes | None = None,
        configuracion: RepositorioConfiguracion | None = None,
        imprimir: ImprimirComprobante | None = None,
        resumen_del_dia: ResumenDelDia | None = None,
        auditor: Auditor | None = None,
        repo_categorias: RepositorioCategorias | None = None,
        anular_venta: AnularVenta | None = None,
    ) -> None:
        super().__init__(parent)
        self._sesion = sesion or Sesion(USUARIO_DEMO)
        self._cola = cola
        self._publicador = publicador
        self._repo_turnos = repositorio_turnos
        self._repo_productos = repositorio_productos
        self._repo_ventas = repositorio_ventas
        self._registrar_venta = registrar_venta
        self._anular_venta = anular_venta
        self._abrir_turno = abrir_turno
        self._cerrar_turno = cerrar_turno
        self._registrar_movimiento = registrar_movimiento

        self._repo_tickets = repo_tickets
        self._auditoria = auditoria
        self._clientes = repo_clientes
        self._configuracion = configuracion
        self._imprimir = imprimir
        self._resumen_dia = resumen_del_dia
        self._auditor = auditor
        self._categorias = repo_categorias
        self._panel_dia: PanelDelDia | None = None
        self._ayuda_conteo = ""
        # O-25: no se guarda nada hasta haber restaurado lo guardado; si no, el primer
        # refresco al abrir la app sobrescribia los tickets en espera con una lista vacia.
        self._persistir = False
        self._temporizador_codigo: str | None = None
        self._dialogo_peso_abierto = False
        self._tiempos_codigo: list[float] = []  # cuando llego cada tecla del codigo
        # O-01b: varios tickets abiertos a la vez; el activo es `_venta`.
        self._tickets: list[Venta | None] = [None]
        self._numeros = [1]  # numero que muestra la pestana de cada ticket
        self._indice = 0
        self._contador_tickets = 1
        self._cambiando_ticket = False

        self._construir()
        self._refrescar_turno()
        self._refrescar_sync()
        self._nueva_venta(forzar=True)  # D-01a: siempre hay una venta abierta
        self._restaurar_espera()  # O-25
        self.al_mostrar()

    @property
    def _venta(self) -> Venta | None:
        return self._tickets[self._indice]

    @_venta.setter
    def _venta(self, venta: Venta | None) -> None:
        self._tickets[self._indice] = venta

    # ------------------------------------------------------------------ UI --

    def _construir(self) -> None:
        # Barra superior siempre visible: estado del turno y de la sincronizacion.
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=12, pady=(8, 0))
        self._lbl_turno = ttk.Label(barra, text="Sin turno abierto")
        self._lbl_turno.pack(side="left", padx=8)
        # HU-VTA-07: la pantalla indica de forma visible si hay operaciones pendientes.
        ttk.Button(barra, text="Sincronizar", command=self._sincronizar).pack(side="right", padx=4)
        self._lbl_sync = ttk.Label(barra, text="")
        self._lbl_sync.pack(side="right", padx=8)

        # O-21: subpestanas del prototipo v3: Venta, Caja y corte, Resumen del dia.
        self._subpestanas = ttk.Notebook(self)
        self._subpestanas.pack(fill="both", expand=True, padx=4, pady=4)
        tab_venta = ttk.Frame(self._subpestanas)
        tab_caja = ttk.Frame(self._subpestanas)
        tab_resumen = ttk.Frame(self._subpestanas)
        self._subpestanas.add(tab_venta, text="Venta")
        self._subpestanas.add(tab_caja, text="Caja y corte")
        self._subpestanas.add(tab_resumen, text="Resumen del día")
        self._tab_resumen = tab_resumen
        self._construir_caja(tab_caja)
        self._construir_resumen(tab_resumen)

        color, claro = MODULOS_COLOR["F1"]

        # --- Fila de acciones con su tecla, como el prototipo v3 (sobre el tinte del modulo).
        acciones = tk.Frame(tab_venta, bg=claro)
        acciones.pack(fill="x")
        interior = tk.Frame(acciones, bg=claro)
        interior.pack(fill="x", padx=12, pady=8)
        # Cobrar se empaqueta primero: con poco ancho se recortan los otros, nunca este.
        BotonAccion(interior, "Cobrar", self._abrir_cobro, "F12", "primario", color).pack(
            side="right"
        )
        for texto, comando, tecla, variante in (
            ("Nuevo ticket", self._nuevo_ticket, "INS", "normal"),
            ("Buscar producto", self._buscar_producto_ui, "F10", "normal"),
            ("Tickets en espera", self._dialogo_espera, "Ctrl+E", "normal"),
            ("Descuento a la línea", self._dialogo_descuento, "F9", "normal"),
            ("Nota de la venta", self._dialogo_nota, "Ctrl+N", "normal"),
            ("Reimprimir último", self._reimprimir_ultimo, "F8", "normal"),
            ("Borrar línea", self._quitar_linea, "DEL", "peligro"),
        ):
            BotonAccion(interior, texto, comando, tecla, variante, color, PAPEL).pack(
                side="left", padx=(0, 6)
            )

        # O-01b: pestanas de tickets (Ticket 1, Ticket 2...); su contenido es el de abajo.
        self._nb_tickets = ttk.Notebook(tab_venta, height=1)
        self._nb_tickets.add(ttk.Frame(self._nb_tickets), text="Ticket 1")
        self._nb_tickets.pack(fill="x", padx=12, pady=(8, 0))
        self._nb_tickets.bind("<<NotebookTabChanged>>", self._al_cambiar_ticket)

        # --- Codigo del producto: el campo grande donde queda el cursor (el lector escribe solo).
        marco_venta = tk.Frame(
            tab_venta, bg=claro, highlightthickness=1, highlightbackground=LINEA_2
        )
        marco_venta.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(
            marco_venta, text="Código del producto:", bg=claro, fg=color, font=fuente(12, True)
        ).grid(row=0, column=0, padx=(12, 8), pady=10)
        self._entrada_codigo = ttk.Entry(marco_venta, font=fuente(13))
        self._entrada_codigo.grid(row=0, column=1, sticky="ew", pady=10)
        marco_venta.columnconfigure(1, weight=1)
        self._entrada_codigo.bind("<Return>", lambda _e: self._agregar_producto())  # D-03
        # O-02b: al escanear el producto se agrega solo, sin apretar Enter.
        self._entrada_codigo.bind("<KeyRelease>", self._al_escribir_codigo)
        tk.Label(marco_venta, text="Cantidad", bg=claro, fg=TINTA_2).grid(
            row=0, column=2, padx=(14, 4)
        )
        self._entrada_cantidad = ttk.Entry(marco_venta, width=7)
        self._entrada_cantidad.insert(0, "1")
        self._entrada_cantidad.grid(row=0, column=3, padx=(0, 6))
        self._entrada_cantidad.bind("<Return>", lambda _e: self._agregar_producto())
        BotonAccion(
            marco_venta, "Agregar", self._agregar_producto, "", "normal", color, PAPEL
        ).grid(row=0, column=4, padx=4)
        # O-04: con una linea seleccionada, + suma 1 y - resta 1.
        BotonAccion(
            marco_venta, "+", lambda: self._ajustar_cantidad(1), "", "normal", color, PAPEL
        ).grid(row=0, column=5, padx=2)
        BotonAccion(
            marco_venta, "−", lambda: self._ajustar_cantidad(-1), "", "normal", color, PAPEL
        ).grid(row=0, column=6, padx=(2, 6))
        BotonAccion(
            marco_venta, "Cambiar lote", self._cambiar_lote_ui, "F11", "normal", color, PAPEL
        ).grid(row=0, column=7, padx=2)
        BotonAccion(
            marco_venta, "Eliminar ticket", self._eliminar_ticket, "", "peligro", color, PAPEL
        ).grid(row=0, column=8, padx=(2, 12))
        # O-17: atajo F10 para buscar producto (solo cuando F1 esta a la vista).
        self.winfo_toplevel().bind("<F10>", self._atajo_buscar, add="+")
        self.winfo_toplevel().bind("<F8>", self._atajo_imprimir, add="+")
        self.winfo_toplevel().bind("<F11>", self._atajo_cambiar_lote, add="+")
        self.winfo_toplevel().bind("<F12>", self._atajo_cobrar, add="+")
        self.winfo_toplevel().bind("<F9>", self._atajo_descuento, add="+")
        self.winfo_toplevel().bind("<Control-e>", self._atajo_espera, add="+")
        self.winfo_toplevel().bind("<Control-n>", self._atajo_nota, add="+")
        self.winfo_toplevel().bind("<Insert>", self._atajo_nuevo_ticket, add="+")

        # --- Cliente de la venta y vendedora (HU-CLI-02: solo se carga a una cuenta de credito).
        fila_cliente = ttk.Frame(tab_venta)
        fila_cliente.pack(fill="x", padx=12, pady=(8, 0))
        fila_cliente.columnconfigure(0, weight=1)
        fila_cliente.columnconfigure(1, weight=1)
        ttk.Label(fila_cliente, text="Cliente de la venta", foreground=TINTA_2).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(fila_cliente, text="Vendedora", foreground=TINTA_2).grid(
            row=0, column=1, sticky="w", padx=(12, 0)
        )
        self._cliente_nombre = StringVar(value=SIN_CLIENTE)
        self._clientes_por_nombre: dict[str, int] = {}
        self._cb_cliente = ttk.Combobox(
            fila_cliente, textvariable=self._cliente_nombre, values=[SIN_CLIENTE], state="readonly"
        )
        self._cb_cliente.grid(row=1, column=0, sticky="ew")
        self._cb_cliente.bind("<<ComboboxSelected>>", self._al_elegir_cliente)
        self._lbl_vendedora = ttk.Entry(fila_cliente, state="readonly")
        self._lbl_vendedora.grid(row=1, column=1, sticky="ew", padx=(12, 0))
        ttk.Label(
            fila_cliente, text="Solo se carga a una cuenta de crédito", foreground=TINTA_3
        ).grid(row=2, column=0, sticky="w")

        # --- Barra de abajo: productos, Total / Pago con / Cambio y el total a cobrar grande.
        barra_total = tk.Frame(tab_venta, bg=claro)
        barra_total.pack(side="bottom", fill="x")
        self._lbl_cantidad = tk.Label(
            barra_total, text="0", bg=claro, fg=color, font=fuente(22, True), padx=14
        )
        self._lbl_cantidad.pack(side="left")
        self._lbl_cantidad_texto = tk.Label(
            barra_total, text="productos en la venta actual", bg=claro, fg=TINTA
        )
        self._lbl_cantidad_texto.pack(side="left")
        self._lbl_resumen = tk.Label(
            barra_total, text="Total: $0  ·  Pagó con: $0  ·  Cambio: $0", bg=claro, fg=TINTA
        )
        self._lbl_resumen.pack(side="left", padx=28)
        # D-15: el numero grande es lo que hay que cobrar (ya redondeado si hay efectivo).
        bloque = tk.Frame(barra_total, bg=color)
        bloque.pack(side="right", fill="y")
        self._lbl_a_cobrar = tk.Label(
            bloque,
            text="A cobrar: $0",
            bg=color,
            fg="#ffffff",
            font=fuente(20, True),
            padx=22,
            pady=12,
        )
        self._lbl_a_cobrar.pack()
        self._lbl_a_cobrar.config(cursor="hand2")
        self._lbl_a_cobrar.bind("<Button-1>", lambda _e: self._abrir_cobro())

        # El panel de pago ahora es el cuadro de Cobro (F12). Estos widgets siguen existiendo,
        # sin mostrarse, porque `_agregar_pago`, `_quitar_pago` y `_refrescar_ticket` los usan.
        marco_pago = ttk.LabelFrame(self, text="Pago")

        fila_pago = ttk.Frame(marco_pago)
        fila_pago.pack(fill="x")

        self._medio = StringVar(value=MedioPago.EFECTIVO.value)
        self._medio_nombre = StringVar(value=NOMBRES_MEDIO_PAGO[MedioPago.EFECTIVO])
        combo_medio = ttk.Combobox(
            fila_pago,
            textvariable=self._medio_nombre,
            values=[NOMBRES_MEDIO_PAGO[m] for m in MedioPago],
            width=16,
            state="readonly",
        )
        combo_medio.grid(row=0, column=0, padx=4, pady=6)
        combo_medio.bind("<<ComboboxSelected>>", self._al_cambiar_medio)

        ttk.Label(fila_pago, text="Monto").grid(row=0, column=1, padx=4, pady=6)
        self._entrada_monto_pago = ttk.Entry(fila_pago, width=10)
        self._entrada_monto_pago.grid(row=0, column=2, padx=4, pady=6)
        self._entrada_monto_pago.bind("<Return>", lambda _e: self._agregar_pago())

        ttk.Button(fila_pago, text="Agregar pago", command=self._agregar_pago).grid(
            row=0, column=3, padx=8, pady=6
        )
        ttk.Button(fila_pago, text="Quitar pago", command=self._quitar_pago).grid(
            row=0, column=4, padx=4, pady=6
        )
        # HU-VTA-06: «Cobrar e imprimir ticket» o «Cobrar solo registrando la venta».
        ttk.Button(
            fila_pago, text="Cobrar e imprimir ticket", command=lambda: self._cerrar_venta(True)
        ).grid(row=0, column=5, padx=4, pady=6)
        ttk.Button(
            fila_pago, text="Cobrar solo registrando", command=lambda: self._cerrar_venta(False)
        ).grid(row=0, column=6, padx=4, pady=6)

        # D-18a: los pagos ya agregados quedan listados y se pueden quitar.
        self._lista_pagos = Listbox(marco_pago, height=2, highlightthickness=0, borderwidth=1)
        self._lista_pagos.pack(fill="x", padx=4, pady=(0, 6))

        columnas = (
            "codigo",
            "nombre",
            "precio",
            "cantidad",
            "descuento",
            "subtotal",
            "existencia",
            "lote",
        )
        anchos = {
            "codigo": 110,
            "nombre": 220,
            "precio": 90,
            "cantidad": 70,
            "descuento": 70,
            "subtotal": 100,
            "existencia": 80,
            "lote": 260,  # O-37: «L-B (vence 09-01-2027) · elegido» cabe completo
        }
        self._tabla = ttk.Treeview(tab_venta, columns=columnas, show="headings", height=4)
        for col, titulo in zip(
            columnas,
            (
                "Código de barras",
                "Descripción del producto",
                "Precio",
                "Cant.",
                "Dcto.",
                "Importe",
                "Existencia",
                "Lote",
            ),
            strict=True,
        ):
            self._tabla.heading(col, text=titulo)
            numerica = col in ("precio", "cantidad", "descuento", "subtotal", "existencia")
            self._tabla.column(col, width=anchos[col], anchor="e" if numerica else "w")
        self._tabla.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        self._tabla.bind("<Delete>", lambda _e: self._quitar_linea())
        self._tabla.bind("<BackSpace>", lambda _e: self._quitar_linea())
        for tecla in ("<plus>", "<KP_Add>"):
            self._tabla.bind(tecla, lambda _e: self._ajustar_cantidad(1))
        for tecla in ("<minus>", "<KP_Subtract>"):
            self._tabla.bind(tecla, lambda _e: self._ajustar_cantidad(-1))

    # --------------------------------------------------------- Sincronizacion --

    def _refrescar_sync(self) -> None:
        if self._cola is None:
            self._lbl_sync.config(text="Sin sincronizacion")
            return
        pendientes = len(self._cola.pendientes())
        destino = "" if self._publicador is not None else " (sin Supabase configurado)"
        self._lbl_sync.config(
            text="Todo sincronizado" if pendientes == 0 else f"Pendientes: {pendientes}{destino}"
        )
        self._publicar_estado()

    def _publicar_estado(self) -> None:
        """Repite en la barra de estado de la ventana la sincronizacion y la jornada."""
        barra = getattr(self.winfo_toplevel(), "actualizar_estado", None)
        if callable(barra):
            barra(
                "Sincronizado"
                if "sincronizado" in self._lbl_sync.cget("text").lower()
                else self._lbl_sync.cget("text"),
                self._lbl_turno.cget("text"),
            )

    def _sincronizar(self) -> None:
        if self._cola is None or self._publicador is None:
            messagebox.showwarning(
                "Sincronización", "No hay Supabase configurado (variable SUPABASE_DB_URL)"
            )
            return
        resultado = SincronizarPendientes(self._cola, self._publicador).ejecutar()
        self._refrescar_sync()
        if resultado.fallo_en is not None:
            messagebox.showwarning(
                "Sincronización",
                f"Se sincronizaron {resultado.sincronizadas} operaciones y luego se corto "
                "(sin conexion o error del servidor). Lo pendiente se reintenta despues; "
                "no se pierde nada.",
            )

    # -------------------------------------------------------------- Turno --

    def _refrescar_turno(self) -> None:
        turno = self._repo_turnos.obtener_abierto()
        ventas_turno: list = []  # las ventas del turno se leen una sola vez por refresco
        for fila in self._tabla_movimientos.get_children():
            self._tabla_movimientos.delete(fila)
        if turno is None:
            self._lbl_turno.config(text="Sin turno abierto")
            self._lbl_en_caja.config(text="En caja: -")
        else:
            self._lbl_turno.config(
                text=f"Turno #{turno.id} abierto - fondo inicial "
                f"{_formatear_clp(turno.fondo_inicial.monto)}"
            )
            # O-23: fondo + ventas en efectivo - vueltos + ingresos - retiros.
            ventas = ventas_turno = self._repo_ventas.obtener_por_turno(turno.id)
            esperado = calcular_arqueo(turno, ventas, Dinero(0)).efectivo_esperado
            self._lbl_en_caja.config(text=f"En caja: {_formatear_clp(esperado)}")
            for movimiento in turno.movimientos:  # O-24
                self._tabla_movimientos.insert(
                    "",
                    "end",
                    values=(
                        movimiento.creado_en.strftime("%H:%M"),
                        movimiento.tipo.value.capitalize(),
                        _formatear_clp(movimiento.monto.monto),
                        movimiento.motivo,
                        self._sesion.nombre or f"usuario {turno.usuario_id}",
                    ),
                )
        self._publicar_estado()
        self._refrescar_corte(turno, ventas_turno)
        self._refrescar_resumen()

    def _construir_caja(self, padre: ttk.Frame) -> None:
        """Corte y arqueo de caja (prototipo v3): acciones, venta de la jornada y dinero en caja."""
        # La pestaña es más alta que la ventana en pantallas chicas: con scroll, nada se recorta.
        desplazable = MarcoDesplazable(padre)
        desplazable.pack(fill="both", expand=True)
        padre = desplazable.interior
        color, claro = MODULOS_COLOR["F1"]
        acciones = tk.Frame(padre, bg=claro)
        acciones.pack(fill="x")
        interior = tk.Frame(acciones, bg=claro)
        interior.pack(fill="x", padx=12, pady=8)
        for texto, comando, tecla in (
            ("Abrir jornada", self._abrir_turno_ui, ""),
            ("Movimiento de caja", self._movimiento_ui, ""),
            ("Anular venta", self._anular_venta_ui, ""),  # HU-VTA-11
            ("Imprimir corte", self._imprimir_corte, "F8"),
        ):
            BotonAccion(interior, texto, comando, tecla, "normal", color, PAPEL).pack(
                side="left", padx=(0, 6)
            )
        BotonAccion(
            interior, "Hacer corte de hoy", self._cerrar_turno_ui, "", "primario", color
        ).pack(side="left", padx=6)

        info = ttk.Frame(padre)
        info.pack(fill="x", padx=12, pady=(10, 0))
        hoy = date.today()
        dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
        meses = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        ttk.Label(
            info,
            text=f"Día: {dias[hoy.weekday()]}, {hoy.day} de {meses[hoy.month - 1]} de {hoy.year}",
        ).pack(side="left")
        self._lbl_cajera = ttk.Label(info, text="")
        self._lbl_cajera.pack(side="left", padx=24)
        self._lbl_estado_jornada = ttk.Label(info, text="", font=fuente(11, True))
        self._lbl_estado_jornada.pack(side="left")

        columnas = ttk.Frame(padre)
        columnas.pack(fill="x", padx=12, pady=8)
        izquierda = ttk.LabelFrame(columnas, text="Venta del turno", padding=8)
        izquierda.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._tabla_jornada = ttk.Treeview(
            izquierda, columns=("medio", "monto"), show="headings", height=6
        )
        self._tabla_jornada.heading("medio", text="Medio de pago")
        self._tabla_jornada.heading("monto", text="Monto")
        self._tabla_jornada.column("medio", width=210, anchor="w")
        self._tabla_jornada.column("monto", width=130, anchor="e")
        self._tabla_jornada.pack(fill="x")
        derecha = ttk.LabelFrame(columnas, text="Dinero en caja", padding=8)
        derecha.pack(side="left", fill="both", expand=True)
        self._filas_dinero: dict[str, ttk.Label] = {}
        for fila, nombre in enumerate(
            (
                "Fondo inicial",
                "Ventas en efectivo",
                "Abonos de clientes",
                "Movimientos de caja",
            )
        ):
            ttk.Label(derecha, text=nombre, foreground=TINTA_2).grid(row=fila, column=0, sticky="w")
            etiqueta = ttk.Label(derecha, text="-")
            etiqueta.grid(row=fila, column=1, sticky="e", padx=(30, 0))
            self._filas_dinero[nombre] = etiqueta
        derecha.columnconfigure(1, weight=1)
        self._lbl_en_caja = ttk.Label(derecha, text="En caja: -", font=fuente(14, True))
        self._lbl_en_caja.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(
            derecha,
            text="Efectivo esperado = fondo + ventas en efectivo + abonos ± movimientos.",
            foreground=TINTA_3,
            wraplength=300,
        ).grid(row=5, column=0, columnspan=2, sticky="w")

        medios = ttk.Frame(padre)
        medios.pack(fill="x", padx=12)
        conciliar = ttk.LabelFrame(medios, text="Para conciliar con el terminal TUU", padding=8)
        conciliar.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._tabla_conciliar = ttk.Treeview(
            conciliar, columns=("concepto", "monto"), show="headings", height=2
        )
        self._tabla_conciliar.heading("concepto", text="Concepto")
        self._tabla_conciliar.heading("monto", text="Monto")
        self._tabla_conciliar.column("concepto", width=260, anchor="w")
        self._tabla_conciliar.column("monto", width=110, anchor="e")
        self._tabla_conciliar.pack(fill="x")
        departamentos = ttk.LabelFrame(medios, text="Ventas por departamento", padding=8)
        departamentos.pack(side="left", fill="both", expand=True)
        self._tabla_departamentos = ttk.Treeview(
            departamentos, columns=("departamento", "monto", "parte"), show="headings", height=3
        )
        for clave, titulo, ancho, ancla in (
            ("departamento", "Departamento", 170, "w"),
            ("monto", "Monto", 100, "e"),
            ("parte", "Participación", 90, "e"),
        ):
            self._tabla_departamentos.heading(clave, text=titulo)
            self._tabla_departamentos.column(clave, width=ancho, anchor=ancla)
        self._tabla_departamentos.pack(fill="x")

        ttk.Label(padre, text="Movimientos del turno").pack(anchor="w", padx=14, pady=(8, 0))
        columnas_mov = ("hora", "tipo", "monto", "motivo", "usuario")
        self._tabla_movimientos = ttk.Treeview(
            padre, columns=columnas_mov, show="headings", height=4
        )
        for col, titulo, ancho in (
            ("hora", "Hora", 70),
            ("tipo", "Tipo", 90),
            ("monto", "Monto", 110),
            ("motivo", "Motivo", 360),
            ("usuario", "Usuario", 120),
        ):
            self._tabla_movimientos.heading(col, text=titulo)
            self._tabla_movimientos.column(col, width=ancho, anchor="w")
        self._tabla_movimientos.pack(fill="both", expand=True, padx=12, pady=4)

        # O-33: cada venta del turno con su nota, para revisarla despues de cobrar.
        ttk.Label(padre, text="Ventas del turno (nota de cada venta)").pack(
            anchor="w", padx=14, pady=(8, 0)
        )
        self._tabla_ventas_turno = ttk.Treeview(
            padre,
            columns=("numero", "hora", "total", "pago", "estado", "nota"),
            show="headings",
            height=4,
        )
        for col, titulo, ancho in (
            ("numero", "N°", 50),
            ("hora", "Hora", 70),
            ("total", "Total", 110),
            ("pago", "Pago", 160),
            ("estado", "Estado", 190),
            ("nota", "Nota", 260),
        ):
            self._tabla_ventas_turno.heading(col, text=titulo)
            self._tabla_ventas_turno.column(col, width=ancho, anchor="w")
        self._tabla_ventas_turno.tag_configure("anulada", foreground="#999999")  # HU-VTA-11
        self._tabla_ventas_turno.pack(fill="both", expand=True, padx=12, pady=(4, 12))

    def _refrescar_corte(self, turno, ventas) -> None:
        """Llena el corte de la jornada: venta por medio, dinero en caja y conciliacion."""
        for tabla in (
            self._tabla_jornada,
            self._tabla_conciliar,
            self._tabla_departamentos,
            self._tabla_ventas_turno,
        ):
            tabla.delete(*tabla.get_children())
        if turno is None:
            self._lbl_estado_jornada.config(text="Sin jornada abierta")
            self._lbl_cajera.config(text="")
            for etiqueta in self._filas_dinero.values():
                etiqueta.config(text="-")
            return
        abonos = Dinero(
            self._clientes.abonos_en_efectivo_del_turno(turno.id) if self._clientes else 0
        )
        arqueo = calcular_arqueo(turno, ventas, Dinero(0), abonos_efectivo=abonos)
        self._lbl_estado_jornada.config(text="Estado: jornada abierta")
        self._lbl_cajera.config(text=f"Cajera: {self._sesion.nombre or turno.usuario_id}")
        total = 0
        for medio, monto in arqueo.totales_por_medio.items():
            nombre = (
                "Cuenta de cliente"
                if medio is MedioPago.CREDITO_CLIENTE
                else (
                    "Tarjeta (terminal TUU)"
                    if medio is MedioPago.TARJETA
                    else NOMBRES_MEDIO_PAGO[medio]
                )
            )
            self._tabla_jornada.insert("", "end", values=(nombre, _formatear_clp(monto.monto)))
            total += monto.monto
        self._tabla_jornada.insert("", "end", values=("Total vendido", _formatear_clp(total)))
        # HU-VTA-11: lo anulado es una partida propia del corte, no «una venta menos».
        self._tabla_jornada.insert(
            "",
            "end",
            values=(
                f"Ventas anuladas ({arqueo.ventas_anuladas})",
                _formatear_clp(arqueo.monto_anulado.monto),
            ),
        )
        movimientos = arqueo.ingresos_caja.monto - arqueo.retiros_caja.monto
        valores = {
            "Fondo inicial": _formatear_clp(turno.fondo_inicial.monto),
            "Ventas en efectivo": "+ "
            + _formatear_clp(arqueo.totales_por_medio[MedioPago.EFECTIVO].monto),
            "Abonos de clientes": "+ " + _formatear_clp(arqueo.abonos_efectivo.monto),
            "Movimientos de caja": ("+ " if movimientos >= 0 else "− ")
            + _formatear_clp(abs(movimientos)),
        }
        for nombre, valor in valores.items():
            self._filas_dinero[nombre].config(text=valor)
        self._tabla_conciliar.insert(
            "",
            "end",
            values=(
                "Tarjeta según el sistema",
                _formatear_clp(arqueo.totales_por_medio[MedioPago.TARJETA].monto),
            ),
        )
        self._tabla_conciliar.insert(
            "",
            "end",
            values=(
                "Abonos de clientes recibidos hoy",
                _formatear_clp(arqueo.abonos_efectivo.monto),
            ),
        )
        por_categoria: dict[str, int] = {}
        for venta in ventas:
            medios = ", ".join(sorted({NOMBRES_MEDIO_PAGO[pago.medio] for pago in venta.pagos}))
            anulada = venta.estado is EstadoVenta.ANULADA
            self._tabla_ventas_turno.insert(
                "",
                "end",
                iid=str(venta.id),
                tags=("anulada",) if anulada else (),
                values=(
                    venta.id,
                    venta.creado_en.strftime("%H:%M"),
                    _formatear_clp(venta.total.monto),
                    medios,
                    f"Anulada · {venta.motivo_anulacion}" if anulada else "Cobrada",
                    venta.nota or "",
                ),
            )
            if anulada:
                continue  # una venta anulada no suma a las ventas por departamento
            for detalle in venta.detalles:
                producto = self._repo_productos.obtener_por_codigo(detalle.producto_codigo)
                nombre = (
                    self._categorias.nombre_de(producto.categoria_id)
                    if producto and self._categorias
                    else None
                ) or "Sin categoría"
                por_categoria[nombre] = por_categoria.get(nombre, 0) + detalle.subtotal.monto
        suma = sum(por_categoria.values())
        for nombre, monto in sorted(por_categoria.items(), key=lambda x: -x[1]):
            parte = f"{monto / suma * 100:.1f}%".replace(".", ",") if suma else "0%"
            self._tabla_departamentos.insert(
                "", "end", values=(nombre, _formatear_clp(monto), parte)
            )

    def _construir_resumen(self, padre: ttk.Frame) -> None:
        """Resumen del dia (prototipo v3). Sin los casos de uso queda un resumen minimo."""
        if self._resumen_dia is not None and self._configuracion is not None:
            self._panel_dia = PanelDelDia(
                padre,
                self._resumen_dia,
                self._configuracion,
                self._auditor,
                ir_a_venta=lambda: self._subpestanas.select(0),
                ir_a=self._ir_a_modulo,
            )
            self._panel_dia.pack(fill="both", expand=True)
            return
        self._lbl_resumen_dia = ttk.Label(padre, text="", font=fuente(12, True))
        self._lbl_resumen_dia.pack(anchor="w", padx=14, pady=(12, 4))

    def _ir_a_modulo(self, destino: str) -> None:
        """Lleva a otro modulo (y a su pestana) desde un aviso o un boton del resumen."""
        ventana = self.winfo_toplevel()
        modulo, pestana = {
            "alertas": ("F3", "alertas"),
            "existencias": ("F3", "existencias"),
            "productos": ("F2", "sin_costo"),
            "reportes": ("F6", ""),
        }.get(destino, ("", ""))
        if modulo and hasattr(ventana, "ir_a"):
            ventana.ir_a(modulo, pestana)

    def _refrescar_resumen(self) -> None:
        if self._panel_dia is not None:
            self._panel_dia.refrescar()
            return
        turno = self._repo_turnos.obtener_abierto()
        if turno is None:
            self._lbl_resumen_dia.config(text="Sin turno abierto")
            return
        ventas = [
            v
            for v in self._repo_ventas.obtener_por_turno(turno.id)
            if v.estado is EstadoVenta.PAGADA
        ]
        total = sum(v.total.monto for v in ventas)
        self._lbl_resumen_dia.config(text=f"{len(ventas)} venta(s) · total {_formatear_clp(total)}")

    def _contar_denominaciones_ui(self, titulo: str) -> ConteoDenominaciones | None:
        """Dialogo de conteo por billete/moneda (HU-CAJ-01/02, hallazgo E-06).

        Devuelve `None` si se cancela; un `ConteoDenominaciones` (incluso vacio,
        total $0) si se confirma.
        """
        dialogo = Toplevel(self)
        dialogo.title(titulo)
        dialogo.transient(self.winfo_toplevel())
        dialogo.grab_set()

        if self._ayuda_conteo:
            ttk.Label(dialogo, text=self._ayuda_conteo, foreground="#666").grid(
                row=len(DENOMINACIONES_CLP) + 2, column=0, columnspan=2, pady=(0, 6)
            )
        entradas: dict[int, ttk.Entry] = {}
        for fila, denominacion in enumerate(DENOMINACIONES_CLP):
            ttk.Label(dialogo, text=_formatear_clp(denominacion)).grid(
                row=fila, column=0, padx=8, pady=3, sticky="w"
            )
            entrada = ttk.Entry(dialogo, width=8)
            entrada.insert(0, "0")
            # O-22: al entrar a la casilla se selecciona el 0 y lo escrito lo reemplaza.
            entrada.bind(
                "<FocusIn>", lambda e: e.widget.after(1, e.widget.selection_range, 0, "end")
            )
            entrada.grid(row=fila, column=1, padx=8, pady=3)
            entradas[denominacion] = entrada

        fila_total = len(DENOMINACIONES_CLP)
        lbl_total = ttk.Label(dialogo, text="Total: $0", font=("TkDefaultFont", 11, "bold"))
        lbl_total.grid(row=fila_total, column=0, columnspan=2, pady=8)

        resultado: dict[str, ConteoDenominaciones | None] = {"valor": None}

        def _leer_conteo() -> dict[int, int]:
            conteo: dict[int, int] = {}
            for denominacion, entrada in entradas.items():
                try:
                    cantidad = int(entrada.get().strip() or "0")
                except ValueError:
                    cantidad = 0
                if cantidad > 0:
                    conteo[denominacion] = cantidad
            return conteo

        def recalcular(*_args: object) -> None:
            conteo = _leer_conteo()
            total = sum(denominacion * cantidad for denominacion, cantidad in conteo.items())
            lbl_total.config(text=f"Total: {_formatear_clp(total)}")

        for entrada in entradas.values():
            entrada.bind("<KeyRelease>", recalcular)

        def confirmar() -> None:
            resultado["valor"] = ConteoDenominaciones(_leer_conteo())
            dialogo.destroy()

        dialogo.bind("<Return>", lambda _e: confirmar())  # O-29
        dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
        ttk.Button(dialogo, text="Confirmar", command=confirmar).grid(
            row=fila_total + 1, column=0, pady=8
        )
        ttk.Button(dialogo, text="Cancelar", command=dialogo.destroy).grid(
            row=fila_total + 1, column=1, pady=8
        )

        recalcular()
        self.wait_window(dialogo)
        return resultado["valor"]

    def _abrir_turno_ui(self) -> None:
        if self._configuracion is not None:
            habitual = self._configuracion.obtener("fondo_habitual")
            self._ayuda_conteo = f"Fondo de caja habitual: {_formatear_clp(habitual)}"
        conteo = self._contar_denominaciones_ui("Abrir turno - contar fondo inicial")
        self._ayuda_conteo = ""
        if conteo is None:
            return
        try:
            self._abrir_turno.ejecutar(
                usuario_id=self._sesion.usuario_id,
                fondo_inicial=Dinero(conteo.total),
                composicion_fondo_inicial=conteo,
            )
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo abrir el turno", str(exc))
            return
        self._refrescar_turno()
        self._refrescar_sync()
        # D-01a: si la app arranco sin turno (lo normal), la venta recien puede
        # iniciarse una vez que se abre uno; no quedaba ninguna forma de que se
        # iniciara sola despues de este punto.
        if self._venta is None:
            self._nueva_venta(forzar=True)
        self._restaurar_espera()  # O-25: los tickets guardados vuelven al abrir el turno

    def _cerrar_turno_ui(self) -> None:
        # O-30: la advertencia es informativa: se puede volver a los tickets o descartarlos.
        pendientes = self._tickets_sin_cobrar()
        if pendientes and not self._confirmar_descartar_tickets(pendientes):
            return
        conteo = self._contar_denominaciones_ui("Cerrar turno - contar efectivo")
        if conteo is None:
            return
        try:
            arqueo = self._cerrar_turno.ejecutar(efectivo_contado=Dinero(conteo.total))
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo cerrar el turno", str(exc))
            return
        if pendientes:
            self._descartar_tickets(pendientes)
        detalle = "\n".join(
            f"{NOMBRES_MEDIO_PAGO[medio]}: {_formatear_clp(monto.monto)}"
            for medio, monto in arqueo.totales_por_medio.items()
        )
        messagebox.showinfo(
            "Arqueo de cierre",
            f"{detalle}\n\n"
            f"Ventas anuladas: {arqueo.ventas_anuladas} por "
            f"{_formatear_clp(arqueo.monto_anulado.monto)}\n"
            f"Abonos de clientes en efectivo: {_formatear_clp(arqueo.abonos_efectivo.monto)}\n"
            f"Efectivo esperado: {_formatear_clp(arqueo.efectivo_esperado)}\n"
            f"Efectivo contado: {_formatear_clp(arqueo.efectivo_contado.monto)}\n"
            f"Diferencia: {_formatear_clp(arqueo.diferencia)}",
        )
        self._refrescar_turno()

    # ------------------------------------------------------------ Anular venta (HU-VTA-11) --

    def ejecutar_anulacion(self, venta_id: int, motivo: str, detalle: str = "") -> bool:
        """Anula la venta con el caso de uso; los errores salen como aviso, sin romper nada."""
        if self._anular_venta is None:
            return False
        quien = self._sesion.nombre or f"usuario {self._sesion.usuario_id}"
        try:
            self._anular_venta.ejecutar(venta_id, motivo, detalle, quien)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo anular la venta", str(exc))
            return False
        self._refrescar_turno()
        self._refrescar_ticket()  # la existencia de los productos cambio
        return True

    def _anular_venta_ui(self) -> None:
        if self._anular_venta is None:
            return
        if self._sesion.rol is not None and self._sesion.rol is not Rol.ADMIN:
            messagebox.showinfo("Anular venta", "Solo la administradora puede anular una venta.")
            return
        turno = self._repo_turnos.obtener_abierto()
        if turno is None:
            messagebox.showinfo("Anular venta", "No hay una jornada abierta.")
            return
        cobradas = [
            v
            for v in self._repo_ventas.obtener_por_turno(turno.id)
            if v.estado is EstadoVenta.PAGADA
        ]
        if not cobradas:
            messagebox.showinfo("Anular venta", "No hay ventas cobradas en esta jornada.")
            return

        dialogo = Toplevel(self)
        dialogo.title("Anular venta")
        dialogo.transient(self.winfo_toplevel())
        dialogo.grab_set()
        ttk.Label(
            dialogo,
            text="Elige la venta cobrada de esta jornada que se anula. No se borra: queda marcada.",
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w")
        tabla = ttk.Treeview(
            dialogo,
            columns=("numero", "hora", "total", "pago"),
            show="headings",
            height=7,
            selectmode="browse",
        )
        for col, titulo, ancho in (
            ("numero", "N°", 50),
            ("hora", "Hora", 70),
            ("total", "Total", 110),
            ("pago", "Pago", 220),
        ):
            tabla.heading(col, text=titulo)
            tabla.column(col, width=ancho, anchor="w")
        for venta in reversed(cobradas):  # la mas reciente arriba
            medios = ", ".join(sorted({NOMBRES_MEDIO_PAGO[p.medio] for p in venta.pagos}))
            tabla.insert(
                "",
                "end",
                iid=str(venta.id),
                values=(
                    venta.id,
                    venta.creado_en.strftime("%H:%M"),
                    _formatear_clp(venta.total.monto),
                    medios,
                ),
            )
        tabla.grid(row=1, column=0, columnspan=2, padx=12, pady=4)
        tabla.selection_set(tabla.get_children()[0])

        ttk.Label(dialogo, text="Motivo").grid(row=2, column=0, padx=12, pady=6, sticky="w")
        motivo_var = StringVar(value=MOTIVOS_ANULACION[0])
        combo = ttk.Combobox(
            dialogo, textvariable=motivo_var, values=MOTIVOS_ANULACION, state="readonly", width=34
        )
        combo.grid(row=2, column=1, padx=12, pady=6, sticky="w")
        ttk.Label(dialogo, text="Cuál fue (si es «Otro»)").grid(
            row=3, column=0, padx=12, pady=6, sticky="w"
        )
        detalle_var = StringVar()
        entrada = ttk.Entry(dialogo, textvariable=detalle_var, width=36, state="disabled")
        entrada.grid(row=3, column=1, padx=12, pady=6, sticky="w")

        def al_cambiar_motivo(_evento: object = None) -> None:
            otro = motivo_var.get() == MOTIVO_OTRO
            entrada.config(state="normal" if otro else "disabled")
            if otro:
                entrada.focus_set()
            else:
                detalle_var.set("")

        combo.bind("<<ComboboxSelected>>", al_cambiar_motivo)

        def confirmar(_evento: object = None) -> None:
            seleccion = tabla.selection()
            if not seleccion:
                messagebox.showwarning(
                    "Anular venta", "Elige la venta que se anula.", parent=dialogo
                )
                return
            venta_id = int(seleccion[0])
            total = tabla.item(seleccion[0], "values")[2]
            if not messagebox.askyesno(
                "Anular venta",
                f"Se anula la venta N° {venta_id} por {total}.\n\n"
                "La existencia de sus productos vuelve al lote del que salió y, si fue a crédito, "
                "se revierte en la cuenta del cliente. No se puede deshacer.\n\n¿Anular?",
                parent=dialogo,
            ):
                return
            if self.ejecutar_anulacion(venta_id, motivo_var.get(), detalle_var.get()):
                dialogo.destroy()
                messagebox.showinfo("Venta anulada", f"La venta N° {venta_id} quedó anulada.")

        botones = ttk.Frame(dialogo)
        botones.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(botones, text="Anular venta", command=confirmar).pack(side="left", padx=6)
        ttk.Button(botones, text="Cancelar", command=dialogo.destroy).pack(side="left", padx=6)
        dialogo.bind("<Escape>", lambda _e: dialogo.destroy())

    def _movimiento_ui(self) -> None:
        # E-03: un solo dialogo con tipo, motivo de una lista, observacion y monto,
        # en vez de tres ventanas sucesivas con motivo en texto libre.
        dialogo = Toplevel(self)
        dialogo.title("Movimiento de caja")
        dialogo.transient(self.winfo_toplevel())
        dialogo.grab_set()

        ttk.Label(dialogo, text="Tipo").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        tipo_var = StringVar(value=TipoMovimientoCaja.RETIRO.value)
        combo_tipo = ttk.Combobox(
            dialogo,
            textvariable=tipo_var,
            values=[t.value for t in TipoMovimientoCaja],
            state="readonly",
            width=20,
        )
        combo_tipo.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(dialogo, text="Motivo").grid(row=1, column=0, padx=8, pady=6, sticky="w")
        motivos_iniciales = MOTIVOS_POR_TIPO[TipoMovimientoCaja(tipo_var.get())]
        motivo_var = StringVar(value=motivos_iniciales[0])
        combo_motivo = ttk.Combobox(
            dialogo, textvariable=motivo_var, values=motivos_iniciales, state="readonly", width=36
        )
        combo_motivo.grid(row=1, column=1, padx=8, pady=6)

        def al_cambiar_tipo(_evento: object = None) -> None:
            motivos = MOTIVOS_POR_TIPO[TipoMovimientoCaja(tipo_var.get())]
            combo_motivo.config(values=motivos)
            motivo_var.set(motivos[0])

        combo_tipo.bind("<<ComboboxSelected>>", al_cambiar_tipo)

        ttk.Label(dialogo, text="Observacion").grid(row=2, column=0, padx=8, pady=6, sticky="w")
        entrada_obs = ttk.Entry(dialogo, width=38)
        entrada_obs.grid(row=2, column=1, padx=8, pady=6)

        ttk.Label(dialogo, text="Monto (CLP)").grid(row=3, column=0, padx=8, pady=6, sticky="w")
        entrada_monto = ttk.Entry(dialogo, width=16)
        entrada_monto.grid(row=3, column=1, padx=8, pady=6)

        dialogo.bind("<Return>", lambda _e: confirmar())  # O-29
        dialogo.bind("<Escape>", lambda _e: dialogo.destroy())

        def confirmar() -> None:
            try:
                monto = parsear_monto(entrada_monto.get())
                if monto <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Monto inválido", "El monto debe ser un entero mayor a cero")
                return
            tipo = TipoMovimientoCaja(tipo_var.get())
            observacion = entrada_obs.get().strip()
            motivo = f"{motivo_var.get()}{' - ' + observacion if observacion else ''}"
            try:
                self._registrar_movimiento.ejecutar(tipo, Dinero(monto), motivo)
            except ErrorDominio as exc:
                messagebox.showerror("No se pudo registrar el movimiento", str(exc))
                return
            dialogo.destroy()
            self._refrescar_turno()
            messagebox.showinfo(
                "Movimiento registrado",
                f"{tipo_var.get().capitalize()} de {_formatear_clp(monto)} registrado",
            )

        ttk.Button(dialogo, text="Registrar", command=confirmar).grid(
            row=4, column=0, columnspan=2, pady=10
        )

    def _ver_ventas_turno(self) -> None:
        # E-08: la venta de la jornada se ve sin cerrar el turno (subpestana Resumen del dia).
        self._refrescar_resumen()
        self._subpestanas.select(self._tab_resumen)

    # -------------------------------------------------------------- Venta --

    def _nueva_venta(self, forzar: bool = False) -> None:
        venta_previa = self._venta
        tiene_contenido = venta_previa is not None and (venta_previa.detalles or venta_previa.pagos)
        # D-01b: no descartar un ticket con productos o pagos sin confirmar.
        if (
            tiene_contenido
            and not forzar
            and not messagebox.askyesno(
                "Descartar venta en curso",
                "La venta actual tiene productos o pagos sin cobrar. "
                "¿Descartarla y empezar una nueva?",
            )
        ):
            return
        try:
            self._venta = self._registrar_venta.iniciar(usuario_id=self._sesion.usuario_id)
        except ErrorDominio as exc:
            self._venta = None
            if not forzar:
                messagebox.showerror("No se pudo iniciar la venta", str(exc))
        self._entrada_cantidad.delete(0, "end")
        self._entrada_cantidad.insert(0, "1")
        # O-27: cada venta nueva parte con Efectivo, el medio por defecto.
        self._medio.set(MedioPago.EFECTIVO.value)
        self._medio_nombre.set(NOMBRES_MEDIO_PAGO[MedioPago.EFECTIVO])
        self._refrescar_ticket()
        self._entrada_codigo.focus_set()

    # ---------------------------------------------------------- Tickets (O-01b) --

    def _reiniciar_medio(self) -> None:
        self._entrada_cantidad.delete(0, "end")
        self._entrada_cantidad.insert(0, "1")
        self._medio.set(MedioPago.EFECTIVO.value)  # O-27: cada ticket parte con Efectivo
        self._medio_nombre.set(NOMBRES_MEDIO_PAGO[MedioPago.EFECTIVO])

    def _en_venta(self) -> bool:
        return bool(self.winfo_ismapped() and self._subpestanas.index("current") == 0)

    def _atajo_cobrar(self, _evento: object = None) -> None:
        """F12 Cobrar (prototipo): abre el cuadro de Cobro, solo con F1 Venta a la vista."""
        if self._en_venta():
            self._abrir_cobro()

    def _atajo_descuento(self, _evento: object = None) -> None:
        if self._en_venta():
            self._dialogo_descuento()

    def _atajo_espera(self, _evento: object = None) -> None:
        if self._en_venta():
            self._dialogo_espera()

    def _atajo_nota(self, _evento: object = None) -> None:
        if self._en_venta():
            self._dialogo_nota()

    # --------------------------------- Cobro, descuento, nota y espera (prototipo v3) --

    def _abrir_cobro(self) -> DialogoCobro | None:
        venta = self._venta_actual()
        if venta is None:
            return None
        if not venta.detalles:
            messagebox.showwarning("Cobrar", "El ticket no tiene productos")
            return None
        return DialogoCobro(self)

    def _dialogo_descuento(self) -> DialogoDescuento | None:
        venta = self._venta_actual()
        codigo = self._linea_seleccionada() if venta is not None else None
        if venta is None:
            return None
        if codigo is None:
            messagebox.showwarning("Descuento a la línea", "Elige una línea del ticket")
            return None
        return DialogoDescuento(self, codigo)

    def _registrar_descuento(self, detalle) -> None:
        """Queda en la auditoria con el importe antes y despues y el motivo."""
        if self._auditoria is None:
            return
        producto = self._repo_productos.obtener_por_codigo(detalle.producto_codigo)
        bruto = detalle.precio_unitario.multiplicado_por(detalle.cantidad).monto
        self._auditoria.registrar(
            self._sesion.nombre or str(self._sesion.usuario_id),
            "Descuento a la línea",
            {"motivo": detalle.motivo_descuento, "descuento": detalle.descuento_linea.monto},
            registro=f"{producto.nombre if producto else detalle.producto_codigo}",
            antes=_formatear_clp(bruto),
            despues=_formatear_clp(detalle.subtotal.monto),
        )

    def _dialogo_nota(self):
        venta = self._venta_actual()
        if venta is None:
            return None

        def guardar(valores: dict[str, str]) -> bool:
            venta.nota = valores["nota"].strip()
            return True

        return pedir_formulario(
            self,
            "Nota de la venta",
            [("nota", "Nota", venta.nota, None)],
            guardar,
            "Guardar nota",
            nota="Queda guardada junto al ticket, en la auditoría y en el comprobante impreso.",
        )

    def _dialogo_espera(self) -> DialogoEspera:
        return DialogoEspera(self)

    def _ir_a_ticket(self, indice: int) -> None:
        if indice == self._indice or not 0 <= indice < len(self._tickets):
            return
        self._cambiando_ticket = True
        self._nb_tickets.select(indice)
        self._cambiando_ticket = False
        self._indice = indice
        self._reiniciar_medio()
        self._refrescar_ticket()
        self._entrada_codigo.focus_set()

    def _existencia_de(self, producto) -> str:
        """Existencia del producto para la tabla; el granel se muestra como «granel»."""
        if producto is None:
            return "—"
        if producto.unidad_venta is UnidadVenta.GRANEL:
            return "granel"
        existencia = self._registrar_venta.repositorio_existencias.obtener(producto.codigo)
        return format(existencia.cantidad.normalize(), "f") if existencia else "0"

    # ------------------------------------- Cliente, vendedora y cabecera de la venta --

    def _refrescar_clientes_combo(self) -> None:
        activos = [c for c in (self._clientes.listar() if self._clientes else []) if c.activo]
        self._clientes_por_nombre = {c.nombre: c.id for c in activos}
        self._cb_cliente.config(values=[SIN_CLIENTE, *self._clientes_por_nombre])

    def _al_elegir_cliente(self, _evento: object = None) -> None:
        if self._venta is not None:
            self._venta.cliente_id = self._clientes_por_nombre.get(self._cliente_nombre.get())

    def _sincronizar_cabecera_venta(self) -> None:
        """Cliente elegido, vendedora, cuantos productos y el subtitulo «Ticket 3 · 3 abiertos»."""
        venta = self._venta
        nombre = SIN_CLIENTE
        if venta is not None and venta.cliente_id is not None and self._clientes:
            cliente = self._clientes.obtener(venta.cliente_id)
            nombre = cliente.nombre if cliente else SIN_CLIENTE
        self._cliente_nombre.set(nombre)
        cantidad = len(venta.detalles) if venta is not None else 0
        self._lbl_cantidad.config(text=str(cantidad))
        self._lbl_cantidad_texto.config(
            text="producto en la venta actual" if cantidad == 1 else "productos en la venta actual"
        )
        barra = getattr(self.winfo_toplevel(), "fijar_subtitulo", None)
        if callable(barra):
            abiertos = len(self._tickets)
            barra(
                f"Ticket {self._numeros[self._indice]} · {abiertos} abierto{'s' * (abiertos != 1)}"
            )

    def al_mostrar(self) -> None:
        self._refrescar_clientes_combo()
        self._lbl_vendedora.config(state="normal")
        self._lbl_vendedora.delete(0, "end")
        self._lbl_vendedora.insert(0, (self._sesion.nombre or "").capitalize())
        self._lbl_vendedora.config(state="readonly")
        self._sincronizar_cabecera_venta()
        self._refrescar_turno()  # el corte nombra a la cajera de ahora

    def _atajo_nuevo_ticket(self, _evento: object = None) -> None:
        if self.winfo_ismapped() and self._subpestanas.index("current") == 0:
            self._nuevo_ticket()

    def _nuevo_ticket(self) -> None:
        """Abre otro ticket; el anterior queda en espera en su pestana."""
        try:
            venta = self._registrar_venta.iniciar(usuario_id=self._sesion.usuario_id)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo iniciar el ticket", str(exc))
            return
        self._tickets.append(venta)
        self._contador_tickets += 1
        self._numeros.append(self._contador_tickets)
        marco = ttk.Frame(self._nb_tickets)
        self._nb_tickets.add(marco, text=f"Ticket {self._contador_tickets}")
        self._cambiando_ticket = True
        self._nb_tickets.select(marco)
        self._cambiando_ticket = False
        self._indice = len(self._tickets) - 1
        self._reiniciar_medio()
        self._refrescar_ticket()
        self._entrada_codigo.focus_set()

    def _al_cambiar_ticket(self, _evento: object = None) -> None:
        if self._cambiando_ticket:
            return
        self._indice = self._nb_tickets.index("current")
        self._reiniciar_medio()
        self._refrescar_ticket()
        self._entrada_codigo.focus_set()

    def _quitar_ticket_actual(self) -> None:
        """Quita el ticket activo; si era el unico, queda uno nuevo y vacio."""
        if len(self._tickets) == 1:
            self._nueva_venta(forzar=True)
            return
        indice = self._indice
        self._cambiando_ticket = True
        self._nb_tickets.forget(indice)
        del self._tickets[indice]
        del self._numeros[indice]
        self._indice = min(indice, len(self._tickets) - 1)
        self._nb_tickets.select(self._indice)
        self._cambiando_ticket = False
        self._reiniciar_medio()
        self._refrescar_ticket()

    def _eliminar_ticket(self) -> None:
        """Solo se pregunta al eliminar un ticket que tiene productos o pagos."""
        venta = self._venta
        if (
            venta is not None
            and (venta.detalles or venta.pagos)
            and not messagebox.askyesno(
                "Eliminar ticket", "El ticket tiene productos o pagos sin cobrar. ¿Eliminarlo?"
            )
        ):
            return
        self._quitar_ticket_actual()

    def _guardar_espera(self) -> None:
        """O-25: conserva los tickets con productos para reabrirlos (nunca los pagos)."""
        if self._repo_tickets is None or not self._persistir:
            return
        self._repo_tickets.guardar(
            [
                {
                    "productos": [[d.producto_codigo, str(d.cantidad)] for d in venta.detalles],
                    "lotes": dict(venta.lote_elegido),
                }
                for venta in self._tickets
                if venta is not None and venta.detalles
            ]
        )

    def _restaurar_espera(self) -> None:
        """O-25: al abrir la app vuelven los tickets que quedaron sin cobrar.

        Sin turno abierto no se restaura ni se guarda nada (los tickets siguen guardados y
        vuelven cuando se abre el turno).
        """
        if self._repo_tickets is None or self._repo_turnos.obtener_abierto() is None:
            return
        guardados = self._repo_tickets.cargar()
        for posicion, ticket in enumerate(guardados):
            if posicion > 0:
                self._nuevo_ticket()
            venta = self._venta
            if venta is None:
                continue
            for codigo, cantidad in ticket["productos"]:
                try:
                    self._registrar_venta.agregar_producto(venta, codigo, Decimal(cantidad))
                except ErrorDominio:
                    continue  # el stock o el producto cambiaron: se omite la linea
            venta.lote_elegido.update(ticket.get("lotes", {}))
        self._persistir = True
        if guardados:
            self._cambiando_ticket = True
            self._nb_tickets.select(0)
            self._cambiando_ticket = False
            self._indice = 0
        self._refrescar_ticket()

    # ------------------------------------------- Cierre de jornada con tickets (O-30) --

    def _tickets_sin_cobrar(self) -> list[Venta]:
        return [v for v in self._tickets if v is not None and v.detalles]

    def _confirmar_descartar_tickets(self, pendientes: list[Venta]) -> bool:
        """Avisa cuantos tickets quedan y su total; False si se prefiere volver a ellos."""
        total = sum(v.total.monto for v in pendientes)
        cantidad = len(pendientes)
        if cantidad == 1:
            cuantos = "Queda 1 ticket sin cobrar"
        else:
            cuantos = f"Quedan {cantidad} tickets sin cobrar"
        if messagebox.askyesno(
            "Tickets sin cobrar",
            f"{cuantos} por {_formatear_clp(total)}.\n\n"
            "¿Descartarlos y cerrar la jornada?\n"
            "Elige «No» para volver a ellos.",
        ):
            return True
        self._subpestanas.select(0)
        return False

    def _descartar_tickets(self, pendientes: list[Venta]) -> None:
        """Deja constancia en la auditoria (sin tocar existencias) y limpia los tickets."""
        if self._auditoria is not None:
            self._auditoria.registrar(
                self._sesion.nombre or str(self._sesion.usuario_id),
                "tickets_descartados_al_cerrar_jornada",
                registro=f"{len(pendientes)} ticket{'s' if len(pendientes) != 1 else ''}",
                antes=_formatear_clp(sum(v.total.monto for v in pendientes)),
                despues="descartados",
                detalle={
                    "cantidad": len(pendientes),
                    "total": sum(v.total.monto for v in pendientes),
                    "tickets": [
                        [
                            {
                                "codigo": d.producto_codigo,
                                "cantidad": str(d.cantidad),
                                "subtotal": d.subtotal.monto,
                            }
                            for d in v.detalles
                        ]
                        for v in pendientes
                    ],
                },
            )
        for _ in range(len(self._tickets) - 1):
            self._nb_tickets.forget(len(self._tickets) - 1)
            self._tickets.pop()
        self._tickets[0] = None
        self._numeros = [1]
        self._contador_tickets = 1
        self._indice = 0
        self._cambiando_ticket = True
        self._nb_tickets.select(0)
        self._cambiando_ticket = False
        self._nueva_venta(forzar=True)  # con la jornada cerrada queda sin venta

    def _venta_actual(self) -> Venta | None:
        if self._venta is None:
            messagebox.showwarning("Sin venta", "Primero inicia una venta nueva")
        return self._venta

    def _agregar_producto(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        self._cancelar_autoagregado()
        codigo = self._entrada_codigo.get().strip()
        if not codigo:
            return
        try:
            # D-07: la Product Owner pidio aceptar coma y punto como separador.
            texto_cantidad = self._entrada_cantidad.get().strip().replace(",", ".")
            cantidad = Decimal(texto_cantidad or "1")
        except InvalidOperation:
            messagebox.showerror("Cantidad inválida", "La cantidad debe ser un número")
            return
        producto = self._repo_productos.obtener_por_codigo(codigo)
        if producto is not None and not producto.activo:
            # O-31: se avisa al escanearlo o elegirlo, antes de pedir el peso o la cantidad.
            messagebox.showerror(
                "No se pudo agregar el producto", f"El producto {producto.nombre} está desactivado"
            )
            self._entrada_codigo.delete(0, "end")
            self._entrada_codigo.focus_set()
            return
        if producto is not None and producto.unidad_venta is UnidadVenta.GRANEL:
            # O-02b: a granel siempre se pide el peso (con el importe a la vista).
            cantidad = self._pedir_peso(producto)
            if cantidad is None:
                return
        try:
            self._registrar_venta.agregar_producto(venta, codigo, cantidad)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo agregar el producto", str(exc))
            return
        self._entrada_codigo.delete(0, "end")
        self._tiempos_codigo = []
        self._entrada_cantidad.delete(0, "end")
        self._entrada_cantidad.insert(0, "1")  # D-23
        self._refrescar_ticket()
        self._entrada_codigo.focus_set()  # D-24

    # ------------------------------------------- Escaneo y peso a granel (O-02b) --

    def _al_escribir_codigo(self, evento: object) -> None:
        if getattr(evento, "keysym", "") in ("Return", "KP_Enter", "Tab", "Escape"):
            return
        self._cancelar_autoagregado()
        ahora = time.monotonic()
        # Un codigo nuevo empieza cuando el campo estaba vacio o hace rato que no se tecleaba.
        if len(self._entrada_codigo.get()) <= 1 or (
            self._tiempos_codigo and ahora - self._tiempos_codigo[-1] > 1.0
        ):
            self._tiempos_codigo = []
        self._tiempos_codigo.append(ahora)
        self._temporizador_codigo = self.after(150, self._autoagregar)

    def _llego_a_ritmo_de_lector(self, codigo: str) -> bool:
        """Un lector entrega el codigo entero en una rafaga (teclas a menos de 80 ms) o pegado de
        una vez. A mano, a ritmo normal, el codigo puede quedar a medias: ahi se espera el Enter
        (si no, el principio de «1050» agregaria el producto «10» y «50» daria «no existe»)."""
        tiempos = self._tiempos_codigo
        if len(tiempos) <= 1:
            return len(codigo) >= 3  # pegado de una vez; con 1 o 2 caracteres no se arriesga
        return len(tiempos) >= len(codigo) and all(
            b - a <= 0.08 for a, b in zip(tiempos, tiempos[1:], strict=False)
        )

    def _cancelar_autoagregado(self) -> None:
        if self._temporizador_codigo is not None:
            self.after_cancel(self._temporizador_codigo)
            self._temporizador_codigo = None

    def _autoagregar(self) -> None:
        """Agrega solo cuando lo escrito es exactamente un producto y no el comienzo de otro."""
        self._temporizador_codigo = None
        codigo = self._entrada_codigo.get().strip()
        if not codigo or self._dialogo_peso_abierto or self._venta is None:
            return
        if self._repo_productos.obtener_por_codigo(codigo) is None:
            return
        if not self._llego_a_ritmo_de_lector(codigo):
            return  # escribiendo a mano: se agrega con Enter
        if any(
            p.codigo != codigo and p.codigo.startswith(codigo)
            for p in self._repo_productos.listar()
        ):
            return  # podria faltar un digito: se espera el Enter
        self._agregar_producto()

    def _pedir_peso(self, producto) -> Decimal | None:
        """Cuadro que pide el peso (kg) de un producto a granel y muestra el importe."""
        self._dialogo_peso_abierto = True
        resultado: list[Decimal] = []
        ventana = Toplevel(self)
        ventana.title("Peso del producto")
        ventana.transient(self.winfo_toplevel())
        ventana.resizable(False, False)
        ttk.Label(
            ventana,
            text=f"{producto.nombre}\nPrecio por kilo: {_formatear_clp(producto.precio.monto)}",
            padding=(16, 12, 16, 4),
        ).pack()
        marco = ttk.Frame(ventana, padding=(16, 4))
        marco.pack()
        ttk.Label(marco, text="Peso (kg)").grid(row=0, column=0, padx=4)
        entrada = ttk.Entry(marco, width=10)
        entrada.grid(row=0, column=1, padx=4)
        importe = ttk.Label(marco, text="Importe: $0", font=("TkDefaultFont", 12, "bold"))
        importe.grid(row=1, column=0, columnspan=2, pady=(8, 0))
        error = ttk.Label(ventana, text="", foreground="#a11")
        error.pack()

        def peso_ingresado() -> Decimal | None:
            texto = entrada.get().strip().replace(",", ".")
            try:
                peso = Decimal(texto)
            except InvalidOperation:
                return None
            return peso if peso > 0 else None

        def recalcular(*_args: object) -> None:
            peso = peso_ingresado()
            monto = producto.precio.multiplicado_por(peso).monto if peso is not None else 0
            importe.config(text=f"Importe: {_formatear_clp(monto)}")

        def cerrar() -> None:
            self._dialogo_peso_abierto = False
            ventana.destroy()

        def confirmar(_evento: object = None) -> None:
            peso = peso_ingresado()
            if peso is None:
                error.config(text="Escribe el peso en kilos (por ejemplo 0,350)")
                return
            resultado.append(peso)
            cerrar()

        entrada.bind("<KeyRelease>", recalcular)
        ventana.bind("<Return>", confirmar)  # Enter confirma, Esc cancela (O-29)
        ventana.bind("<Escape>", lambda _e: cerrar())
        ventana.protocol("WM_DELETE_WINDOW", cerrar)
        botones = ttk.Frame(ventana, padding=(16, 4, 16, 12))
        botones.pack()
        ttk.Button(botones, text="Agregar", command=confirmar).pack(side="left", padx=4)
        ttk.Button(botones, text="Cancelar", command=cerrar).pack(side="left", padx=4)
        ventana.grab_set()
        entrada.focus_set()
        self.wait_window(ventana)
        self._dialogo_peso_abierto = False
        return resultado[0] if resultado else None

    def _quitar_linea(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        seleccion = self._tabla.selection()
        if not seleccion:
            messagebox.showwarning("Sin selección", "Selecciona una línea del ticket")
            return
        codigo = self._tabla.item(seleccion[0], "values")[0]
        try:
            venta.quitar_detalle(codigo)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo quitar la línea", str(exc))
            return
        self._refrescar_ticket()

    def _buscar_producto_ui(self) -> None:
        # D-26: encontrar un producto por nombre cuando no tiene codigo de barras
        # o el lector no lo lee, sin distinguir tildes ni mayusculas.
        dialogo = Toplevel(self)
        dialogo.title("Buscar producto")
        dialogo.transient(self.winfo_toplevel())
        dialogo.grab_set()
        # O-38: alto fijo; lo que sobra se desplaza con barra y los botones siempre se ven.
        dialogo.geometry("420x440")
        dialogo.minsize(380, 360)

        ttk.Label(dialogo, text="Nombre").pack(padx=8, pady=(8, 2), anchor="w")
        entrada = ttk.Entry(dialogo, width=40)
        entrada.pack(padx=8, pady=2, fill="x")
        entrada.focus_set()

        # Los botones y el aviso se empacan primero, abajo, para que la lista no los desplace.
        pie = ttk.Frame(dialogo)
        pie.pack(side="bottom", fill="x", pady=(0, 8))
        marco_lista = ttk.Frame(dialogo)
        marco_lista.pack(padx=8, pady=8, fill="both", expand=True)
        barra = ttk.Scrollbar(marco_lista, orient="vertical")
        barra.pack(side="right", fill="y")
        lista = Listbox(marco_lista, width=50, height=8, yscrollcommand=barra.set)
        lista.pack(side="left", fill="both", expand=True)
        barra.configure(command=lista.yview)

        productos = self._repo_productos.listar()

        def refrescar_lista(*_args: object) -> None:
            termino = _normalizar(entrada.get().strip())
            lista.delete(0, "end")
            coinciden = [p for p in productos if termino in _normalizar(p.nombre)]
            # CA-15: primero los que empiezan con lo escrito (p. ej. «Té verde» al buscar «te»).
            coinciden.sort(
                key=lambda p: (rango_de_busqueda(p.nombre, termino), _normalizar(p.nombre))
            )
            for producto in coinciden:
                # O-31: un producto desactivado se distingue en la lista (texto y color gris).
                aviso = "" if producto.activo else " (desactivado)"
                lista.insert("end", f"{producto.codigo} - {producto.nombre}{aviso}")
                if not producto.activo:
                    lista.itemconfig("end", foreground="#999999")

        def elegir(_evento: object = None) -> None:
            seleccion = lista.curselection()
            if not seleccion:
                return
            codigo = lista.get(seleccion[0]).split(" - ", 1)[0]
            elegido = self._repo_productos.obtener_por_codigo(codigo)
            if elegido is not None and not elegido.activo:
                # O-31: el aviso sale al elegirlo, antes de agregar y de pedir cantidad o peso.
                messagebox.showerror(
                    "No se pudo agregar el producto",
                    f"El producto {elegido.nombre} está desactivado",
                )
                return
            self._entrada_codigo.delete(0, "end")
            self._entrada_codigo.insert(0, codigo)
            dialogo.destroy()
            if elegido is not None and elegido.unidad_venta is UnidadVenta.GRANEL:
                # O-32: un granel elegido en F10 pide el peso de inmediato y entra al ticket.
                self._agregar_producto()
                return
            self._entrada_cantidad.focus_set()

        def elegir_con_enter(_evento: object = None) -> None:
            if not lista.curselection() and lista.size():
                lista.selection_set(0)  # Enter sin elegir toma el primero de la lista
            elegir()

        boton = ttk.Button(pie, text="Seleccionar", command=elegir)

        def rotular_boton(_evento: object = None) -> None:
            # O-32: si lo resaltado es granel, el boton avisa que se pedira el peso.
            seleccion = lista.curselection()
            granel = False
            if seleccion:
                codigo = lista.get(seleccion[0]).split(" - ", 1)[0]
                elegido = self._repo_productos.obtener_por_codigo(codigo)
                granel = elegido is not None and elegido.unidad_venta is UnidadVenta.GRANEL
            boton.configure(text="A granel · pedir peso" if granel else "Seleccionar")

        entrada.bind("<KeyRelease>", refrescar_lista)
        lista.bind("<Double-Button-1>", elegir)
        lista.bind("<<ListboxSelect>>", rotular_boton)
        dialogo.bind("<Return>", elegir_con_enter)  # O-29
        dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
        refrescar_lista()

        ttk.Label(
            pie,
            text="Si el producto es a granel, al aceptar se pide el peso.",
            foreground="#666666",
        ).pack(padx=8)
        boton.pack(pady=(4, 0))

    def _rotular_pestanas(self) -> None:
        """HU-VTA-05: cada pestana muestra el total de su ticket (p. ej. «Ticket 1 · $18.240»)."""
        for posicion, venta in enumerate(self._tickets):
            texto = f"Ticket {self._numeros[posicion]}"
            if venta is not None and venta.detalles:
                texto += f" · {_formatear_clp(venta.total.monto)}"
            self._nb_tickets.tab(posicion, text=texto)

    def _refrescar_ticket(self) -> None:
        self._rotular_pestanas()
        self._sincronizar_cabecera_venta()
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        venta = self._venta
        self._lista_pagos.delete(0, "end")

        if venta is None:
            self._lbl_a_cobrar.config(text="A cobrar: $0")
            self._lbl_resumen.config(text="Total: $0  ·  Pagó con: $0  ·  Cambio: $0")
            self._guardar_espera()
            return

        for detalle in venta.detalles:
            producto = self._repo_productos.obtener_por_codigo(detalle.producto_codigo)
            nombre = producto.nombre if producto else "?"
            self._tabla.insert(
                "",
                "end",
                values=(
                    detalle.producto_codigo,
                    nombre,
                    _formatear_clp(detalle.precio_unitario.monto)
                    + ("/kg" if producto and producto.unidad_venta is UnidadVenta.GRANEL else ""),
                    detalle.cantidad,
                    _formatear_clp(detalle.descuento_linea.monto)
                    if detalle.descuento_linea.monto
                    else "—",
                    _formatear_clp(detalle.subtotal.monto),
                    self._existencia_de(producto),
                    self._texto_lote(venta, detalle.producto_codigo),
                ),
            )

        for indice, pago in enumerate(venta.pagos):
            self._lista_pagos.insert(
                "end",
                f"{indice + 1}. {NOMBRES_MEDIO_PAGO[pago.medio]}: "
                f"{_formatear_clp(pago.monto.monto)}",
            )

        a_cobrar = self._a_cobrar_visible(venta)
        pagado = venta.total_pagado.monto
        self._lbl_a_cobrar.config(text=f"A cobrar: {_formatear_clp(a_cobrar)}")
        self._lbl_resumen.config(
            text=f"Total: {_formatear_clp(venta.total.monto)}  ·  "
            f"Pagó con: {_formatear_clp(pagado)}  ·  "
            f"Cambio: {_formatear_clp(venta.vuelto_entregado.monto)}"
        )

        # D-19: proponer el saldo pendiente como monto por defecto; la cajera
        # solo lo cambia si es un pago parcial.
        saldo = max(0, a_cobrar - pagado)
        self._entrada_monto_pago.delete(0, "end")
        if saldo:
            self._entrada_monto_pago.insert(0, _formatear_clp(saldo).lstrip("$"))
        self._guardar_espera()

    def _a_cobrar_visible(self, venta: Venta) -> int:
        """O-27: con efectivo (el medio por defecto) se muestra desde el inicio el total
        redondeado a la decena, el mismo que despues exige el cierre de la venta."""
        if venta.tiene_pago_en_efectivo or self._medio.get() == MedioPago.EFECTIVO.value:
            return redondear_a_decena(venta.total.monto)
        return venta.total.monto

    def _al_cambiar_medio(self, _evento: object = None) -> None:
        por_nombre = {nombre: medio for medio, nombre in NOMBRES_MEDIO_PAGO.items()}
        self._medio.set(por_nombre[self._medio_nombre.get()].value)
        self._refrescar_ticket()

    def _texto_lote(self, venta: Venta, codigo: str) -> str:
        """I-03: lote que sale con la linea (el que vence antes, o el elegido con F5)."""
        lote = self._registrar_venta.lote_para(venta, codigo)
        if lote is None:
            return "-"
        # O-37: «123 (vence 13-11)»; si se eligio a mano con F11 se dice con una palabra.
        elegido = " · elegido" if venta.lote_elegido.get(codigo) == lote.uuid else ""
        vence = formatear_fecha_corta(lote.fecha_vencimiento)
        return f"{lote.etiqueta} (vence {vence}){elegido}"

    def _linea_seleccionada(self) -> str | None:
        seleccion = self._tabla.selection()
        if not seleccion:
            messagebox.showwarning("Sin selección", "Selecciona una línea del ticket")
            return None
        return str(self._tabla.item(seleccion[0], "values")[0])

    def _ajustar_cantidad(self, delta: int) -> None:
        """O-04: + suma 1 y - resta 1 sobre la linea seleccionada; en 0 pregunta si quitarla."""
        venta = self._venta_actual()
        codigo = self._linea_seleccionada() if venta is not None else None
        if venta is None or codigo is None:
            return
        detalle = next(d for d in venta.detalles if d.producto_codigo == codigo)
        try:
            if delta < 0 and detalle.cantidad + delta <= 0:
                if messagebox.askyesno(
                    "Quitar línea", f"La cantidad llegaría a 0. Quitar {codigo}?"
                ):
                    venta.quitar_detalle(codigo)
            else:
                self._registrar_venta.agregar_producto(venta, codigo, delta)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo cambiar la cantidad", str(exc))
        self._refrescar_ticket()
        for fila in self._tabla.get_children():  # mantiene la seleccion para seguir con +/-
            if self._tabla.item(fila, "values")[0] == codigo:
                self._tabla.selection_set(fila)

    def _atajo_cambiar_lote(self, _evento: object = None) -> None:
        if self.winfo_ismapped() and self._subpestanas.index("current") == 0:
            self._cambiar_lote_ui()

    def _cambiar_lote_ui(self) -> None:
        """O-28: F11 Cambiar lote (F5 es Compras). Lista los lotes con saldo y deja elegir uno."""
        venta = self._venta_actual()
        codigo = self._linea_seleccionada() if venta is not None else None
        if venta is None or codigo is None:
            return
        lotes = self._registrar_venta.lotes_de(codigo)
        if not lotes:
            messagebox.showinfo("Lotes", "Este producto no tiene lotes con vencimiento")
            return
        dialogo = Toplevel(self)
        dialogo.title(f"Cambiar lote - {codigo}")
        dialogo.transient(self.winfo_toplevel())
        dialogo.grab_set()
        lista = Listbox(dialogo, height=min(8, len(lotes)), width=48, exportselection=False)
        for lote in lotes:
            lista.insert(
                "end",
                f"{lote.etiqueta} · vence {formatear_fecha_corta(lote.fecha_vencimiento)} "
                f"· saldo {lote.saldo}",
            )
        lista.selection_set(0)
        lista.pack(padx=12, pady=10)

        def elegir() -> None:
            seleccion = lista.curselection()
            if not seleccion:
                return
            try:
                self._registrar_venta.elegir_lote(venta, codigo, lotes[seleccion[0]].uuid)
            except ErrorDominio as exc:
                messagebox.showerror("No se pudo cambiar el lote", str(exc))
                return
            dialogo.destroy()
            self._refrescar_ticket()

        lista.bind("<Double-Button-1>", lambda _e: elegir())
        dialogo.bind("<Return>", lambda _e: elegir())  # O-29
        dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
        lista.focus_set()
        ttk.Button(dialogo, text="Usar este lote", command=elegir).pack(pady=(0, 10))

    def _atajo_buscar(self, _evento: object = None) -> None:
        """O-17: F10 abre la busqueda de producto si esta pantalla esta a la vista."""
        if self.winfo_ismapped() and self._subpestanas.index("current") == 0:
            self._buscar_producto_ui()

    def _agregar_pago(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        try:
            monto = parsear_monto(self._entrada_monto_pago.get())
        except ValueError:
            messagebox.showerror("Monto inválido", "El monto debe ser un número entero")
            return
        if monto <= 0:  # F-04
            messagebox.showerror("Monto inválido", "El monto debe ser mayor que cero")
            return

        medio = MedioPago(self._medio.get())
        try:
            if medio is MedioPago.EFECTIVO:
                # D-18b: la decision de si es pago parcial o cierra con vuelto
                # vive en el dominio (Venta.construir_pago_efectivo), probada en
                # tests/unitarias/test_ventas.py.
                pago = venta.construir_pago_efectivo(monto_entregado=monto)
                if pago.cobro_efectivo is not None and pago.cobro_efectivo.vuelto.monto:
                    vuelto_fmt = _formatear_clp(pago.cobro_efectivo.vuelto.monto)
                    messagebox.showinfo("Cambio", f"Cambio: {vuelto_fmt}")
            else:
                if medio is MedioPago.CREDITO_CLIENTE and not self._elegir_cliente(venta):
                    return  # HU-CLI-02: sin cliente no hay credito
                pago = Pago(medio=medio, monto=Dinero(monto))
            self._registrar_venta.agregar_pago(venta, pago)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo agregar el pago", str(exc))
            return
        self._refrescar_ticket()

    # --------------------------------------------- Venta a credito (HU-CLI-02) --

    def _elegir_cliente(self, venta: Venta) -> bool:
        """Pide el cliente al que se carga el credito; False si se cancela o no hay clientes."""
        if venta.cliente_id is not None:
            return True
        cliente_id = self._elegir_cliente_ui()
        if cliente_id is None:
            return False
        venta.cliente_id = cliente_id
        return True

    def _elegir_cliente_ui(self) -> int | None:
        activos = [c for c in (self._clientes.listar() if self._clientes else []) if c.activo]
        if not activos:
            messagebox.showwarning(
                "Crédito cliente",
                "No hay clientes con crédito activos. Crea uno en F4 Clientes.",
            )
            return None
        dialogo = Toplevel(self)
        dialogo.title("Cargar a la cuenta de un cliente")
        dialogo.transient(self.winfo_toplevel())
        dialogo.grab_set()
        lista = Listbox(dialogo, height=min(10, len(activos)), width=44, exportselection=False)
        for cliente in activos:
            saldo = saldo_de(self._clientes.movimientos(cliente.id))
            lista.insert("end", f"{cliente.nombre} · saldo {_formatear_clp(saldo)}")
        lista.selection_set(0)
        lista.pack(padx=12, pady=10)
        lista.focus_set()
        elegido: list[int] = []

        def aceptar(_evento: object = None) -> None:
            seleccion = lista.curselection()
            if seleccion:
                elegido.append(activos[seleccion[0]].id)
            dialogo.destroy()

        lista.bind("<Double-Button-1>", aceptar)
        dialogo.bind("<Return>", aceptar)  # Enter acepta, Esc cancela
        dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
        ttk.Button(dialogo, text="Cargar a este cliente", command=aceptar).pack(pady=(0, 10))
        self.wait_window(dialogo)
        return elegido[0] if elegido else None

    # ---------------------------------------------- Impresora y cajon (HU-VTA-06) --

    def _imprimir_tras_cobrar(self, venta: Venta, imprimir: bool) -> None:
        """La venta ya esta registrada: si la impresora falla solo se avisa, nunca se deshace."""
        if self._imprimir is None:
            return
        try:
            if imprimir:
                self._imprimir.comprobante(venta)  # imprime y abre el cajon si hubo efectivo
            else:
                self._imprimir.abrir_cajon_si_hubo_efectivo(venta)  # igual entra plata a la gaveta
        except ErrorImpresion as exc:
            messagebox.showwarning(
                "Impresora", f"La venta #{venta.id} quedo registrada, pero: {exc}"
            )

    def _reimprimir_ultimo(self) -> None:
        if self._imprimir is None:
            messagebox.showwarning("Impresora", "No hay impresora configurada")
            return
        try:
            venta = self._imprimir.reimprimir_ultimo()
        except ErrorImpresion as exc:
            messagebox.showwarning("Impresora", str(exc))
            return
        messagebox.showinfo("Impresora", f"Se reimprimio el comprobante de la venta #{venta.id}")

    def _imprimir_corte(self) -> None:
        turno = self._repo_turnos.obtener_abierto()
        if turno is None or self._imprimir is None:
            messagebox.showwarning("Impresora", "No hay una jornada abierta para imprimir su corte")
            return
        abonos = Dinero(
            self._clientes.abonos_en_efectivo_del_turno(turno.id) if self._clientes else 0
        )
        arqueo = calcular_arqueo(
            turno, self._repo_ventas.obtener_por_turno(turno.id), Dinero(0), abonos_efectivo=abonos
        )
        try:
            self._imprimir.corte(turno, arqueo)
        except ErrorImpresion as exc:
            messagebox.showwarning("Impresora", str(exc))

    def _atajo_imprimir(self, _evento: object = None) -> None:
        """F8: reimprime el ultimo comprobante en Venta, o imprime el corte en Caja y corte."""
        if not self.winfo_ismapped():
            return
        if self._subpestanas.index("current") == 1:
            self._imprimir_corte()
        else:
            self._reimprimir_ultimo()

    def _quitar_pago(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        seleccion = self._lista_pagos.curselection()
        if not seleccion:
            messagebox.showwarning("Sin selección", "Selecciona un pago de la lista")
            return
        try:
            venta.quitar_pago(seleccion[0])
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo quitar el pago", str(exc))
            return
        self._refrescar_ticket()

    def _cerrar_venta(self, imprimir: bool = False) -> bool:
        """Cobra el ticket; devuelve True si la venta quedo registrada."""
        venta = self._venta_actual()
        if venta is None:
            return False
        try:
            self._registrar_venta.cerrar(venta)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo cerrar la venta", str(exc))
            return False
        if venta.nota and self._auditoria is not None:
            self._auditoria.registrar(
                self._sesion.nombre or str(self._sesion.usuario_id),
                "Nota de la venta",
                {},
                registro=f"Venta N° {venta.id}",
                despues=venta.nota,
            )
        self._imprimir_tras_cobrar(venta, imprimir)
        vuelto = venta.vuelto_entregado.monto
        messagebox.showinfo(
            "Venta cerrada",
            f"Venta #{venta.id} registrada con éxito"
            + (f"\nCambio a entregar: {_formatear_clp(vuelto)}" if vuelto else ""),
        )
        self._refrescar_sync()
        self._refrescar_turno()
        self._quitar_ticket_actual()  # D-01a: queda lista para la siguiente
        return True
