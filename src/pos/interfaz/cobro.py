"""Cuadros de la venta del prototipo v3: Cobro, Descuento a la linea y Tickets en espera.

Son cuadros modales (toman el foco con `grab_set`) pero NO bloquean el programa con `wait_window`:
cada accion es un metodo (`agregar_pago`, `cobrar`, `aplicar`...) que la ventana de venta y las
pruebas pueden llamar directo. Toda la regla de negocio vive en el dominio (`Venta`, `Pago`); aqui
solo se lee lo escrito y se muestra el resultado.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_clp, parsear_monto
from pos.dominio.pagos import (
    DENOMINACIONES_CLP,
    NOMBRES_MEDIO,
    ConteoDenominaciones,
    MedioPago,
    Pago,
    redondear_a_decena,
)
from pos.dominio.value_objects import Dinero
from pos.interfaz.tema import (
    LINEA,
    LINEA_2,
    MODULOS_COLOR,
    PAPEL,
    RELLENO,
    TINTA,
    TINTA_2,
    BotonAccion,
    centrar,
    fuente,
)

if TYPE_CHECKING:  # solo para los tipos: evita el import circular con app_ventas
    from pos.interfaz.app_ventas import VentanaVentas

DESCRIPCION_MEDIO = {
    MedioPago.EFECTIVO: "Billetes y monedas",
    MedioPago.TARJETA: "Terminal TUU",
    MedioPago.TRANSFERENCIA: "Medio propio",
    MedioPago.CREDITO_CLIENTE: "Cuenta de un cliente",
}
MOTIVOS_DESCUENTO = ("Cortesía", "Producto dañado", "Cliente frecuente", "Error de precio", "Otro")


def _ventana_modal(host: tk.Misc, titulo: str) -> tk.Toplevel:
    ventana = tk.Toplevel(host)
    ventana.title(titulo)
    ventana.transient(host.winfo_toplevel())
    ventana.configure(bg=PAPEL)
    return ventana


class DialogoCobro(tk.Toplevel):
    """Cobrar el ticket: medio de pago, billetes que entrega el cliente, cambio y acciones."""

    def __init__(self, host: VentanaVentas) -> None:
        super().__init__(host)
        self.host = host
        self.venta = host._venta
        self.title(
            f"Venta de productos: cobrar · Ticket {host._numeros[host._indice]} · "
            f"{len(self.venta.detalles)} productos"
        )
        self.transient(host.winfo_toplevel())
        self.configure(bg=PAPEL)
        self.resizable(False, False)
        self.medio = MedioPago.EFECTIVO
        self.conteo: dict[int, tk.Entry] = {}
        self._color, self._claro = MODULOS_COLOR["F1"]
        self._mensaje = tk.StringVar()

        principal = tk.Frame(self, bg=PAPEL)
        principal.pack(side="left", fill="both", expand=True, padx=14, pady=12)
        self._total = tk.Label(
            principal, text="", bg=self._claro, fg=self._color, font=fuente(26, True), pady=10
        )
        tk.Label(principal, text="Total a cobrar", bg=PAPEL, fg=TINTA_2).pack(anchor="w")
        self._total.pack(fill="x")

        fila_medios = tk.Frame(principal, bg=PAPEL)
        fila_medios.pack(fill="x", pady=10)
        self._fichas: dict[MedioPago, tk.Frame] = {}
        for medio in MedioPago:
            ficha = tk.Frame(fila_medios, bg=PAPEL, highlightthickness=1, cursor="hand2")
            ficha.pack(side="left", padx=(0, 8), ipadx=8, ipady=4)
            nombre = tk.Label(ficha, text=NOMBRES_MEDIO[medio], bg=PAPEL, font=fuente(11, True))
            nombre.pack()
            detalle = tk.Label(
                ficha, text=DESCRIPCION_MEDIO[medio], bg=PAPEL, fg=TINTA_2, font=fuente(9)
            )
            detalle.pack()
            for pieza in (ficha, nombre, detalle):
                pieza.bind("<Button-1>", lambda _e, m=medio: self.seleccionar_medio(m))
            self._fichas[medio] = ficha

        self._panel = tk.Frame(principal, bg=PAPEL)
        self._panel.pack(fill="x")

        tk.Label(principal, text="Pagos agregados", bg=PAPEL, fg=TINTA_2).pack(
            anchor="w", pady=(10, 2)
        )
        self._tabla = ttk.Treeview(
            principal,
            columns=("medio", "monto", "entrego", "cambio"),
            show="headings",
            height=3,
            selectmode="browse",
        )
        for clave, titulo, ancho, ancla in (
            ("medio", "Medio de pago", 170, "w"),
            ("monto", "Monto", 100, "e"),
            ("entrego", "Entregó", 100, "e"),  # O-36: lo que dio el cliente en efectivo
            ("cambio", "Cambio", 100, "e"),
        ):
            self._tabla.heading(clave, text=titulo)
            self._tabla.column(clave, width=ancho, anchor=ancla)
        self._tabla.pack(fill="x")
        ttk.Button(principal, text="Quitar pago", command=self.quitar_pago).pack(anchor="e", pady=4)
        self._resumen = tk.Label(principal, text="", bg=PAPEL, fg=TINTA, font=fuente(11, True))
        self._resumen.pack(anchor="w", pady=(4, 0))
        tk.Label(principal, textvariable=self._mensaje, bg=PAPEL, fg="#9d3b2f").pack(anchor="w")

        # Barra lateral ACCIONES como el prototipo.
        lateral = tk.Frame(self, bg=RELLENO, highlightthickness=1, highlightbackground=LINEA_2)
        lateral.pack(side="right", fill="y")
        tk.Label(lateral, text="ACCIONES", bg=RELLENO, fg=TINTA_2, font=fuente(9, True)).pack(
            anchor="w", padx=12, pady=(12, 6)
        )
        for texto, comando, tecla, variante in (
            ("Cobrar e imprimir ticket", lambda: self.cobrar(True), "F1", "primario"),
            ("Cobrar solo registrando la venta", lambda: self.cobrar(False), "F2", "normal"),
            ("Ingresar notas", self.ingresar_nota, "Ctrl+N", "normal"),
            ("Cancelar", self.cancelar, "ESC", "normal"),
        ):
            BotonAccion(lateral, texto, comando, tecla, variante, self._color, PAPEL).pack(
                fill="x", padx=12, pady=3
            )
        self._articulos = tk.Label(lateral, text="", bg=RELLENO, fg=TINTA, padx=12)
        self._articulos.pack(anchor="w", pady=(14, 12))

        self.bind("<F1>", lambda _e: self.cobrar(True))
        self.bind("<F2>", lambda _e: self.cobrar(False))
        self.bind("<Control-n>", lambda _e: self.ingresar_nota())
        self.bind("<Escape>", lambda _e: self.cancelar())
        self.bind("<Return>", lambda _e: self.agregar_pago())
        self.seleccionar_medio(MedioPago.EFECTIVO)
        centrar(self, self.host.winfo_toplevel())
        self.grab_set()

    # ------------------------------------------------------------------ montos --

    def _pagado(self) -> int:
        return self.venta.total_pagado.monto

    def _a_cobrar(self) -> int:
        """Lo que hay que cobrar: con efectivo se redondea a la decena (HU-VTA-04)."""
        if self.medio is MedioPago.EFECTIVO or self.venta.tiene_pago_en_efectivo:
            return redondear_a_decena(self.venta.total.monto)
        return self.venta.total.monto

    def saldo(self) -> int:
        return max(0, self._a_cobrar() - self._pagado())

    # ------------------------------------------------------------------ medios --

    def seleccionar_medio(self, medio: MedioPago) -> None:
        self.medio = medio
        for m, ficha in self._fichas.items():
            activo = m is medio
            ficha.config(
                bg=self._claro if activo else PAPEL,
                highlightbackground=self._color if activo else LINEA,
                highlightthickness=2 if activo else 1,
            )
            for pieza in ficha.winfo_children():
                pieza.config(bg=self._claro if activo else PAPEL)
        for pieza in self._panel.winfo_children():
            pieza.destroy()
        self.conteo = {}
        self.ent_monto = None
        self.cb_cliente = None
        if medio is MedioPago.EFECTIVO:
            self._panel_efectivo()
        elif medio is MedioPago.CREDITO_CLIENTE:
            self._panel_credito()
        else:
            self._panel_simple()
        self._actualizar()

    def _boton_agregar(self, padre: tk.Misc) -> None:
        ttk.Button(padre, text="Agregar pago", command=self.agregar_pago).pack(
            anchor="e", pady=(8, 0)
        )

    def _panel_efectivo(self) -> None:
        tk.Label(
            self._panel,
            text="Billetes y monedas que entrega el cliente (o escribe el monto entregado)",
            bg=PAPEL,
            fg=TINTA_2,
        ).pack(anchor="w")
        rejilla = tk.Frame(self._panel, bg=PAPEL)
        rejilla.pack(anchor="w", pady=4)
        for posicion, denominacion in enumerate(DENOMINACIONES_CLP):
            columna, fila = divmod(posicion, 3)
            tk.Label(rejilla, text=formatear_clp(denominacion), bg=PAPEL, width=8, anchor="e").grid(
                row=fila, column=columna * 2, padx=(10, 2), pady=2
            )
            entrada = tk.Entry(rejilla, width=4, justify="right")
            entrada.insert(0, "0")
            entrada.grid(row=fila, column=columna * 2 + 1, pady=2)
            entrada.bind("<KeyRelease>", lambda _e: self._actualizar())
            entrada.bind(
                "<FocusIn>", lambda e: e.widget.after(1, e.widget.selection_range, 0, "end")
            )
            self.conteo[denominacion] = entrada
        linea = tk.Frame(self._panel, bg=PAPEL)
        linea.pack(anchor="w", pady=4)
        tk.Label(linea, text="Monto entregado (sin contar billetes)", bg=PAPEL).pack(side="left")
        self.ent_monto = tk.Entry(linea, width=12, justify="right")
        self.ent_monto.pack(side="left", padx=8)
        self.ent_monto.insert(0, formatear_clp(self.saldo()).lstrip("$"))
        self.ent_monto.bind("<KeyRelease>", lambda _e: self._actualizar())
        self.ent_monto.focus_set()
        self.ent_monto.selection_range(0, "end")
        self._boton_agregar(self._panel)

    def _panel_simple(self) -> None:
        linea = tk.Frame(self._panel, bg=PAPEL)
        linea.pack(anchor="w")
        nombre = "tarjeta" if self.medio is MedioPago.TARJETA else "transferencia"
        tk.Label(linea, text=f"Monto a cobrar en {nombre}", bg=PAPEL).pack(side="left")
        self.ent_monto = tk.Entry(linea, width=12, justify="right")
        self.ent_monto.pack(side="left", padx=8)
        self.ent_monto.insert(0, formatear_clp(self.saldo()).lstrip("$"))
        self.ent_monto.bind("<KeyRelease>", lambda _e: self._actualizar())
        self.ent_monto.focus_set()
        self.ent_monto.selection_range(0, "end")
        texto = (
            "Tarjeta es un solo medio: el terminal TUU no distingue débito de crédito. El monto "
            "se digita en el terminal aparte."
            if self.medio is MedioPago.TARJETA
            else "La transferencia es un medio propio: el corte cuadra sin corregir a mano."
        )
        tk.Label(
            self._panel, text=texto, bg=PAPEL, fg=TINTA_2, wraplength=470, justify="left"
        ).pack(anchor="w", pady=6)
        self._boton_agregar(self._panel)

    def _panel_credito(self) -> None:
        host = self.host
        activos = [c for c in (host._clientes.listar() if host._clientes else []) if c.activo]
        self._clientes = {c.nombre: c.id for c in activos}
        fila = tk.Frame(self._panel, bg=PAPEL)
        fila.pack(anchor="w")
        tk.Label(fila, text="Cliente", bg=PAPEL).grid(row=0, column=0, sticky="w")
        self.var_cliente = tk.StringVar()
        self.cb_cliente = ttk.Combobox(
            fila,
            textvariable=self.var_cliente,
            values=list(self._clientes),
            state="readonly",
            width=28,
        )
        self.cb_cliente.grid(row=1, column=0, padx=(0, 12))
        actual = self.venta.cliente_id
        for nombre, identificador in self._clientes.items():
            if identificador == actual:
                self.var_cliente.set(nombre)
        self.cb_cliente.bind("<<ComboboxSelected>>", lambda _e: self._actualizar())
        tk.Label(fila, text="Monto a cargar a la cuenta", bg=PAPEL).grid(
            row=0, column=1, sticky="w"
        )
        self.ent_monto = tk.Entry(fila, width=12, justify="right")
        self.ent_monto.grid(row=1, column=1)
        self.ent_monto.insert(0, formatear_clp(self.saldo()).lstrip("$"))
        self.ent_monto.bind("<KeyRelease>", lambda _e: self._actualizar())
        self._lbl_saldo_cliente = tk.Label(self._panel, text="", bg=PAPEL, fg=TINTA)
        self._lbl_saldo_cliente.pack(anchor="w", pady=6)
        if not self._clientes:
            tk.Label(
                self._panel,
                text="No hay clientes con crédito activos. Crea uno en F4 Clientes.",
                bg=PAPEL,
                fg="#9d3b2f",
            ).pack(anchor="w")
        self._boton_agregar(self._panel)

    # --------------------------------------------------------------- lectura --

    def _conteo(self) -> dict[int, int]:
        cuenta = {}
        for denominacion, entrada in self.conteo.items():
            try:
                cantidad = int(entrada.get().strip() or "0")
            except ValueError:
                cantidad = 0
            if cantidad > 0:
                cuenta[denominacion] = cantidad
        return cuenta

    def entregado_efectivo(self) -> tuple[int, ConteoDenominaciones | None]:
        """Con billetes contados manda la suma de los billetes; si no, el monto escrito."""
        cuenta = self._conteo()
        if cuenta:
            conteo = ConteoDenominaciones(cuenta)
            return conteo.total, conteo
        try:
            return parsear_monto(self.ent_monto.get()), None
        except ValueError:
            return 0, None

    def _monto_escrito(self) -> int:
        try:
            return parsear_monto(self.ent_monto.get())
        except ValueError:
            return 0

    def _actualizar(self) -> None:
        self._total.config(text=formatear_clp(self._a_cobrar()))
        self._articulos.config(text=f"Total de artículos: {len(self.venta.detalles)}")
        self._tabla.delete(*self._tabla.get_children())
        for pago in self.venta.pagos:
            cobro = pago.cobro_efectivo
            self._tabla.insert(
                "",
                "end",
                values=(
                    NOMBRES_MEDIO[pago.medio],
                    formatear_clp(pago.monto.monto),
                    formatear_clp(cobro.monto_entregado.monto) if cobro else "",
                    formatear_clp(cobro.vuelto.monto) if cobro else "",
                ),
            )
        saldo = self.saldo()
        vuelto = self.venta.vuelto_entregado.monto
        if self.venta.pagos and saldo == 0:
            # O-36: con todo pagado el cambio queda a la vista hasta cerrar la venta (antes
            # volvia a «Pagó con $0 · su cambio $0» apenas se agregaba el pago).
            self._resumen.config(
                text=f"Pagado {formatear_clp(self._pagado())}"
                + (f"  ·  su cambio {formatear_clp(vuelto)}" if vuelto else "")
            )
        elif self.medio is MedioPago.EFECTIVO and self.ent_monto is not None:
            entregado, conteo = self.entregado_efectivo()
            try:
                pago = self.venta.construir_pago_efectivo(
                    monto_entregado=None if conteo else entregado, composicion=conteo
                )
                cambio = pago.cobro_efectivo.vuelto.monto if pago.cobro_efectivo else 0
            except ErrorDominio:
                cambio = 0
            falta = max(0, saldo - entregado)
            self._resumen.config(
                text=f"Pagó con {formatear_clp(entregado)}  ·  "
                + (
                    f"falta {formatear_clp(falta)}"
                    if falta
                    else f"su cambio {formatear_clp(cambio)}"
                )
            )
        elif self.medio is MedioPago.CREDITO_CLIENTE and self.cb_cliente is not None:
            self._actualizar_saldo_cliente()
            self._resumen.config(text=f"Falta cobrar {formatear_clp(saldo)}")
        else:
            self._resumen.config(
                text=f"Pagado {formatear_clp(self._pagado())}  ·  falta {formatear_clp(saldo)}"
                if self.venta.pagos
                else f"Falta cobrar {formatear_clp(saldo)}"
            )

    def _aviso_de_cupo(self, cliente_id: int, monto: int) -> str:
        from pos.dominio.clientes import aviso_cupo_insuficiente, cupo_disponible, saldo_de

        cliente = self.host._clientes.obtener(cliente_id) if self.host._clientes else None
        if cliente is None:
            return ""
        disponible = cupo_disponible(
            cliente.cupo, saldo_de(self.host._clientes.movimientos(cliente_id))
        )
        if disponible is not None and monto > disponible:
            return aviso_cupo_insuficiente(cliente.nombre, disponible, monto)
        return ""

    def _actualizar_saldo_cliente(self) -> None:
        cliente_id = self._clientes.get(self.var_cliente.get())
        if cliente_id is None or not self.host._clientes:
            self._lbl_saldo_cliente.config(text="Elige el cliente al que se carga la venta")
            return
        from pos.dominio.clientes import cupo_disponible, saldo_de

        actual = saldo_de(self.host._clientes.movimientos(cliente_id))
        cliente = self.host._clientes.obtener(cliente_id)
        disponible = cupo_disponible(cliente.cupo if cliente else None, actual)
        cupo = (
            "" if disponible is None else f"  ·  cupo disponible {formatear_clp(disponible)}"
        )  # CL-01
        self._lbl_saldo_cliente.config(
            text=f"Saldo actual {formatear_clp(actual)}  ·  saldo resultante "
            f"{formatear_clp(actual + self._monto_escrito())}{cupo}"
        )

    # ---------------------------------------------------------------- acciones --

    def _error(self, texto: str) -> bool:
        self._mensaje.set(texto)
        messagebox.showerror("Cobrar", texto, parent=self)
        return False

    def agregar_pago(self) -> bool:
        """Agrega el pago del medio elegido (los pagos mixtos se arman de a uno)."""
        self._mensaje.set("")
        try:
            if self.medio is MedioPago.EFECTIVO:
                entregado, conteo = self.entregado_efectivo()
                if entregado <= 0:
                    return self._error("Escribe cuánto entrega el cliente")
                pago = self.venta.construir_pago_efectivo(
                    monto_entregado=None if conteo else entregado, composicion=conteo
                )
            else:
                monto = self._monto_escrito()
                if monto <= 0:
                    return self._error("El monto debe ser mayor que cero")
                if self.medio is MedioPago.CREDITO_CLIENTE:
                    cliente_id = self._clientes.get(self.var_cliente.get())
                    if cliente_id is None:
                        return self._error("Elige el cliente al que se carga el crédito")
                    self.venta.cliente_id = cliente_id
                    aviso = self._aviso_de_cupo(cliente_id, monto)
                    if aviso:  # CL-01: no se carga si pasa el cupo; el aviso dice cuanto queda
                        return self._error(aviso)
                pago = Pago(medio=self.medio, monto=Dinero(monto))
            self.host._registrar_venta.agregar_pago(self.venta, pago)
        except ErrorDominio as exc:
            return self._error(str(exc))
        self.host._refrescar_ticket()
        self.seleccionar_medio(self.medio)  # vuelve a proponer el saldo que falta
        return True

    def quitar_pago(self) -> None:
        seleccion = self._tabla.selection()
        indice = self._tabla.index(seleccion[0]) if seleccion else len(self.venta.pagos) - 1
        if indice < 0:
            return
        try:
            self.venta.quitar_pago(indice)
        except ErrorDominio as exc:
            self._error(str(exc))
            return
        self.host._refrescar_ticket()
        self.seleccionar_medio(self.medio)

    def ingresar_nota(self) -> None:
        self.host._dialogo_nota()

    def cobrar(self, imprimir: bool) -> bool:
        """Cobra el ticket; si falta por cobrar, agrega antes el pago escrito en el cuadro."""
        if self.saldo() > 0 and not self.agregar_pago():
            return False
        if self.host._cerrar_venta(imprimir):
            self.destroy()
            return True
        return False

    def cancelar(self) -> None:
        self.destroy()


class DialogoDescuento(tk.Toplevel):
    """Descuento a la linea seleccionada (porcentaje o monto fijo, con motivo obligatorio)."""

    def __init__(self, host: VentanaVentas, codigo: str) -> None:
        super().__init__(host)
        self.host = host
        self.codigo = codigo
        self.venta = host._venta
        self.detalle = next(d for d in self.venta.detalles if d.producto_codigo == codigo)
        producto = host._repo_productos.obtener_por_codigo(codigo)
        self.title("Descuento a la línea")
        self.transient(host.winfo_toplevel())
        self.configure(bg=PAPEL)
        self.resizable(False, False)
        self._bruto = self.detalle.precio_unitario.multiplicado_por(self.detalle.cantidad).monto

        tk.Label(
            self,
            text=f"{producto.nombre if producto else codigo} · {self.detalle.cantidad} ",
            bg=PAPEL,
            fg=TINTA_2,
        ).grid(row=0, column=0, columnspan=3, padx=14, pady=(12, 6), sticky="w")
        self.var_tipo = tk.StringVar(value="Porcentaje")
        self.var_valor = tk.StringVar(value="")
        self.var_motivo = tk.StringVar(value="")
        for columna, (titulo, widget) in enumerate(
            (
                ("Importe de la línea", tk.Label(self, text=formatear_clp(self._bruto), bg=PAPEL)),
                (
                    "Tipo de descuento",
                    ttk.Combobox(
                        self,
                        textvariable=self.var_tipo,
                        values=["Porcentaje", "Monto fijo"],
                        state="readonly",
                        width=14,
                    ),
                ),
                ("Valor", ttk.Entry(self, textvariable=self.var_valor, width=10)),
            )
        ):
            tk.Label(self, text=titulo, bg=PAPEL, fg=TINTA_2).grid(
                row=1, column=columna, padx=14, sticky="w"
            )
            widget.grid(row=2, column=columna, padx=14, sticky="w")
            if titulo == "Valor":
                widget.focus_set()
        self._lbl_aplicado = tk.Label(self, text="", bg=PAPEL, font=fuente(11, True))
        self._lbl_final = tk.Label(self, text="", bg=PAPEL, font=fuente(11, True))
        tk.Label(self, text="Descuento aplicado", bg=PAPEL, fg=TINTA_2).grid(
            row=3, column=0, padx=14, pady=(10, 0), sticky="w"
        )
        tk.Label(self, text="Importe final", bg=PAPEL, fg=TINTA_2).grid(
            row=3, column=1, padx=14, pady=(10, 0), sticky="w"
        )
        tk.Label(self, text="Motivo (obligatorio)", bg=PAPEL, fg=TINTA_2).grid(
            row=3, column=2, padx=14, pady=(10, 0), sticky="w"
        )
        self._lbl_aplicado.grid(row=4, column=0, padx=14, sticky="w")
        self._lbl_final.grid(row=4, column=1, padx=14, sticky="w")
        ttk.Combobox(
            self, textvariable=self.var_motivo, values=list(MOTIVOS_DESCUENTO), width=18
        ).grid(row=4, column=2, padx=14, sticky="w")
        tk.Label(
            self,
            text="Requisito del prototipo sin validar con la Product Owner. Se guarda como campo "
            "propio (no baja el precio) para que el reporte de rentabilidad diga por qué hay menos "
            "margen. Para liquidar por vencimiento se cambia el precio del producto.",
            bg=PAPEL,
            fg="#7a4a2e",
            wraplength=520,
            justify="left",
        ).grid(row=5, column=0, columnspan=3, padx=14, pady=10, sticky="w")
        botones = tk.Frame(self, bg=PAPEL)
        botones.grid(row=6, column=0, columnspan=3, pady=(0, 12))
        BotonAccion(botones, "Cancelar", self.destroy, "ESC", "normal", host_color(), PAPEL).pack(
            side="left", padx=6
        )
        BotonAccion(
            botones, "Aplicar descuento", self.aplicar, "ENTER", "primario", host_color()
        ).pack(side="left", padx=6)
        self.var_tipo.trace_add("write", lambda *_a: self._recalcular())
        self.var_valor.trace_add("write", lambda *_a: self._recalcular())
        self.bind("<Return>", lambda _e: self.aplicar())
        self.bind("<Escape>", lambda _e: self.destroy())
        self._recalcular()
        centrar(self, self.host.winfo_toplevel())
        self.grab_set()

    def monto(self) -> int:
        """Descuento en pesos segun el tipo y el valor escritos."""
        try:
            valor = float(self.var_valor.get().strip().replace(",", ".") or "0")
        except ValueError:
            return 0
        if self.var_tipo.get() == "Porcentaje":
            return round(self._bruto * valor / 100)
        return round(valor)

    def _recalcular(self) -> None:
        monto = self.monto()
        self._lbl_aplicado.config(text=formatear_clp(monto))
        self._lbl_final.config(text=formatear_clp(max(0, self._bruto - monto)))

    def aplicar(self) -> bool:
        try:
            self.venta.aplicar_descuento(self.codigo, self.monto(), self.var_motivo.get())
        except ErrorDominio as exc:
            messagebox.showerror("Descuento", str(exc), parent=self)
            return False
        self.host._registrar_descuento(self.detalle)
        self.host._refrescar_ticket()
        self.destroy()
        return True


def host_color() -> str:
    return MODULOS_COLOR["F1"][0]


class DialogoEspera(tk.Toplevel):
    """Tickets en espera: los tickets abiertos con su total, para pasar de uno a otro."""

    def __init__(self, host: VentanaVentas) -> None:
        super().__init__(host)
        self.host = host
        self.title("Tickets en espera")
        self.transient(host.winfo_toplevel())
        self.configure(bg=PAPEL)
        tk.Label(
            self,
            text="Los tickets abiertos no descuentan existencia: el stock se mueve al cobrar.",
            bg=PAPEL,
            fg=TINTA_2,
        ).pack(padx=14, pady=(12, 6), anchor="w")
        self.tabla = ttk.Treeview(
            self, columns=("ticket", "productos", "total"), show="headings", height=6
        )
        for clave, titulo, ancho, ancla in (
            ("ticket", "Ticket", 120, "w"),
            ("productos", "Productos", 100, "e"),
            ("total", "Total", 120, "e"),
        ):
            self.tabla.heading(clave, text=titulo)
            self.tabla.column(clave, width=ancho, anchor=ancla)
        self.tabla.pack(padx=14, fill="x")
        for posicion, venta in enumerate(host._tickets):
            self.tabla.insert(
                "",
                "end",
                iid=str(posicion),
                values=(
                    f"Ticket {host._numeros[posicion]}",
                    len(venta.detalles) if venta else 0,
                    formatear_clp(venta.total.monto) if venta else "$0",
                ),
            )
        self.tabla.selection_set(str(host._indice))
        botones = tk.Frame(self, bg=PAPEL)
        botones.pack(pady=12)
        BotonAccion(botones, "Cerrar", self.destroy, "ESC", "normal", host_color(), PAPEL).pack(
            side="left", padx=6
        )
        BotonAccion(botones, "Ir al ticket", self.ir, "ENTER", "primario", host_color()).pack(
            side="left", padx=6
        )
        self.tabla.bind("<Double-Button-1>", lambda _e: self.ir())
        self.bind("<Return>", lambda _e: self.ir())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.tabla.focus_set()
        centrar(self, self.host.winfo_toplevel())
        self.grab_set()

    def ir(self) -> None:
        seleccion = self.tabla.selection()
        if seleccion:
            self.host._ir_a_ticket(int(seleccion[0]))
        self.destroy()
