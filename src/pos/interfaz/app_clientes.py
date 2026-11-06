"""Pantalla F4 Clientes: credito a familiares, su cuenta, estado de cuenta y reporte de saldos.

Cubre HU-CLI-01 (cuenta de credito), HU-CLI-03 (abonos y saldo), HU-CLI-04 (estado de cuenta
mensual) y HU-CLI-05 (reporte de saldos). La venta a credito (HU-CLI-02) se hace desde F1 y el
credito en el cierre de caja (HU-CAJ-03) en el arqueo. El saldo siempre se calcula sumando los
movimientos. Los nombres de las pruebas y demos van enmascarados: no hay datos reales aqui.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.gestionar_clientes import (
    GestionarClientes,
    PagarEstadoDeCuenta,
    RegistrarAbono,
)
from pos.aplicacion.puertos import RepositorioClientes
from pos.dominio.clientes import (
    MEDIO_DESCUENTO,
    PORCENTAJE_DESCUENTO_CREDITO,
    Cliente,
    TipoMovimientoCliente,
    abonos_del_ciclo,
    consumos_del_ciclo,
    descuento_credito,
    en_ciclo,
    saldo_anterior,
    saldo_de,
    total_a_pagar,
    ultimo_consumo,
)
from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_cantidad, formatear_clp, parsear_monto
from pos.interfaz import tema
from pos.interfaz.campo_fecha import CampoFecha
from pos.interfaz.exportar import exportar_con_dialogo

MESES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)
MEDIOS = {"Efectivo": "efectivo", "Transferencia": "transferencia", "Tarjeta": "tarjeta"}


def _fecha(valor: date | None) -> str:
    return valor.strftime("%d-%m-%Y") if valor else "—"


def _rotulo_ciclo(anio: int, mes: int) -> str:
    return f"{MESES[mes - 1]} {anio}"


def _ciclo_de(rotulo: str) -> tuple[int, int]:
    nombre, anio = rotulo.rsplit(" ", 1)
    return int(anio), MESES.index(nombre) + 1


def _ultimos_ciclos(cantidad: int = 12) -> list[str]:
    hoy = date.today()
    ciclos = []
    anio, mes = hoy.year, hoy.month
    for _ in range(cantidad):
        ciclos.append(_rotulo_ciclo(anio, mes))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return ciclos


class VentanaClientes(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        gestion: GestionarClientes,
        abonar: RegistrarAbono,
        repo_clientes: RepositorioClientes,
        pagar_estado: PagarEstadoDeCuenta | None = None,
    ) -> None:
        super().__init__(parent, padding=8)
        self._gestion = gestion
        self._abonar = abonar
        self._repo = repo_clientes
        self._pagador = pagar_estado or PagarEstadoDeCuenta(repo_clientes)
        self._cliente_id: int | None = None  # cliente de la pestana Cuenta / Estado de cuenta
        self._ciclo = tk.StringVar(value=_ultimos_ciclos(1)[0])
        self._ciclo_saldos = tk.StringVar(value=_ultimos_ciclos(1)[0])
        self._buscar = tk.StringVar()
        self._estado = tk.StringVar(value="Activos")
        self._orden = tk.StringVar(value="Mayor saldo")
        self._mensaje = tk.StringVar()

        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True)
        self._construir_lista()
        self._construir_cuenta()
        self._construir_estado()
        self._construir_saldos()
        ttk.Label(self, textvariable=self._mensaje, foreground="#2E6B3E").pack(anchor="w", pady=4)
        self.refrescar()

    # ------------------------------------------------------------- construccion --

    def _tabla(self, padre: tk.Misc, columnas: tuple, altura: int = 12) -> ttk.Treeview:
        tabla = ttk.Treeview(
            padre, columns=[c[0] for c in columnas], show="headings", height=altura
        )
        for clave, titulo, ancho, ancla in columnas:
            tabla.heading(clave, text=titulo)
            tabla.column(clave, width=ancho, anchor=ancla)
        return tabla

    def _construir_lista(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Clientes")
        filtros = ttk.Frame(marco)
        filtros.pack(fill="x")
        ttk.Label(filtros, text="Buscar").grid(row=0, column=0, sticky="w", padx=4)
        entrada = ttk.Entry(filtros, textvariable=self._buscar, width=28)
        entrada.grid(row=1, column=0, padx=4, sticky="w")
        entrada.bind("<KeyRelease>", lambda _e: self._refrescar_lista())
        ttk.Label(filtros, text="Estado").grid(row=0, column=1, sticky="w", padx=4)
        combo_estado = ttk.Combobox(
            filtros,
            textvariable=self._estado,
            values=["Activos", "Inactivos", "Todos"],
            state="readonly",
            width=12,
        )
        combo_estado.grid(row=1, column=1, padx=4)
        ttk.Label(filtros, text="Ordenar").grid(row=0, column=2, sticky="w", padx=4)
        combo_orden = ttk.Combobox(
            filtros,
            textvariable=self._orden,
            values=["Mayor saldo", "Nombre"],
            state="readonly",
            width=14,
        )
        combo_orden.grid(row=1, column=2, padx=4)
        for combo in (combo_estado, combo_orden):
            combo.bind("<<ComboboxSelected>>", lambda _e: self._refrescar_lista())

        botones = tk.Frame(marco, bg=tema.PAPEL)
        botones.pack(fill="x", pady=8)
        for texto, comando, tecla, variante in (
            ("Nuevo cliente", self._nuevo_cliente, "INS", "primario"),
            ("Modificar cliente", self._modificar_cliente, "", "normal"),
            ("Desactivar / reactivar", self._cambiar_estado, "DEL", "peligro"),
            ("Ver cuenta", self._ver_cuenta, "↵", "normal"),
            ("Registrar abono", self._abono_desde_lista, "", "normal"),
        ):
            tema.BotonAccion(
                botones,
                texto,
                comando,
                tecla,
                variante,
                color=tema.MODULOS_COLOR["F4"][0],
                fondo=tema.PAPEL,
            ).pack(side="left", padx=(0, 6))

        self._tabla_lista = self._tabla(
            marco,
            (
                ("n", "N°", 50, "w"),
                ("cliente", "Cliente", 220, "w"),
                ("contacto", "Contacto", 200, "w"),
                ("ultimo", "Último consumo", 120, "w"),
                ("saldo", "Saldo", 110, "e"),
                ("estado", "Estado", 90, "w"),
            ),
        )
        self._tabla_lista.pack(fill="both", expand=True)
        self._tabla_lista.bind("<Double-Button-1>", lambda _e: self._ver_cuenta())

    def _construir_cuenta(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Cuenta")
        cab = ttk.Frame(marco)
        cab.pack(fill="x")
        self._lbl_cliente = ttk.Label(
            cab, text="Elige un cliente en la lista", font=("", 12, "bold")
        )
        self._lbl_cliente.grid(row=0, column=0, sticky="w", padx=4)
        self._lbl_saldo = ttk.Label(cab, text="Saldo actual: -", font=("", 12, "bold"))
        self._lbl_saldo.grid(row=0, column=1, padx=24)
        ttk.Label(cab, text="Ciclo").grid(row=0, column=2, padx=4)
        combo = ttk.Combobox(
            cab, textvariable=self._ciclo, values=_ultimos_ciclos(), state="readonly", width=18
        )
        combo.grid(row=0, column=3, padx=4)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._refrescar_cuenta())
        ttk.Button(cab, text="Registrar abono", command=self._abono_de_la_cuenta).grid(
            row=0, column=4, padx=12
        )
        self._tabla_cuenta = self._tabla(
            marco,
            (
                ("fecha", "Fecha", 100, "w"),
                ("mov", "Movimiento", 120, "w"),
                ("detalle", "Detalle", 280, "w"),
                ("cargo", "Cargo", 100, "e"),
                ("abono", "Abono", 100, "e"),
                ("saldo", "Saldo", 110, "e"),
            ),
        )
        self._tabla_cuenta.tag_configure("linea", foreground="#555")
        self._tabla_cuenta.pack(fill="both", expand=True, pady=8)
        ttk.Label(
            marco,
            text="El saldo no se guarda: se calcula sumando los movimientos. Un movimiento "
            "registrado no se edita; un error se corrige con otro movimiento.",
            foreground="#666",
        ).pack(anchor="w")

    def _construir_estado(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Estado de cuenta")
        self._lbl_estado = ttk.Label(
            marco, text="Elige un cliente en la lista", font=("", 12, "bold")
        )
        self._lbl_estado.pack(anchor="w", padx=4)
        self._tabla_estado = self._tabla(
            marco,
            (
                ("fecha", "Fecha", 100, "w"),
                ("detalle", "Detalle del consumo", 380, "w"),
                ("monto", "Monto", 110, "e"),
            ),
        )
        self._tabla_estado.tag_configure("linea", foreground="#555")
        # Lo de abajo se empaqueta primero: si la ventana es baja, la tabla cede el espacio.
        ttk.Label(
            marco,
            text=f"Al cierre del ciclo se descuenta el {PORCENTAJE_DESCUENTO_CREDITO} % del total "
            "de consumos del mes (HU-CLI-04). Reemitir el estado de cuenta no genera movimientos.",
            foreground="#666",
        ).pack(side="bottom", anchor="w", pady=(8, 0))
        resumen = ttk.Frame(marco)
        resumen.pack(side="bottom", anchor="e")
        self._lbl_resumen = {}
        self._rotulos_resumen = {}
        for fila, (clave, rotulo, negrita) in enumerate(
            (
                ("anterior", "Saldo anterior", False),
                ("consumos", "Consumos del ciclo", False),
                (
                    "descuento",
                    f"Descuento del crédito familiar ({PORCENTAJE_DESCUENTO_CREDITO} %)",
                    False,
                ),
                ("total", "Total a pagar del ciclo", True),
                ("abonos", "Abonos del ciclo", False),
                ("final", "Saldo final", True),
            )
        ):
            fuente = ("", 11, "bold") if negrita else ("", 10)
            etiqueta = ttk.Label(resumen, text=rotulo, font=fuente)
            etiqueta.grid(row=fila, column=0, sticky="e", padx=8)
            self._rotulos_resumen[clave] = etiqueta
            valor = ttk.Label(resumen, text="—", font=fuente, anchor="e", width=14)
            valor.grid(row=fila, column=1, sticky="e")
            self._lbl_resumen[clave] = valor
        botones = ttk.Frame(marco)
        botones.pack(side="bottom", anchor="e", pady=(6, 0))
        ttk.Button(
            botones, text="Registrar pago del estado de cuenta", command=self._pagar_estado
        ).pack(side="left", padx=6)
        ttk.Button(botones, text="Exportar", command=self._exportar_estado).pack(side="left")
        self._tabla_estado.pack(fill="both", expand=True, pady=8)

    def _construir_saldos(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Reporte de saldos")
        cab = ttk.Frame(marco)
        cab.pack(fill="x")
        ttk.Label(cab, text="Ciclo").pack(side="left", padx=4)
        combo = ttk.Combobox(
            cab,
            textvariable=self._ciclo_saldos,
            values=_ultimos_ciclos(),
            state="readonly",
            width=18,
        )
        combo.pack(side="left", padx=4)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._refrescar_saldos())
        self._tabla_saldos = self._tabla(
            marco,
            (
                ("cliente", "Cliente", 220, "w"),
                ("ultimo", "Último consumo", 120, "w"),
                ("consumos", "Consumos del ciclo", 140, "e"),
                ("abonos", "Abonos del ciclo", 130, "e"),
                ("saldo", "Saldo", 110, "e"),
            ),
        )
        self._tabla_saldos.pack(fill="both", expand=True, pady=8)
        self._lbl_total_saldos = ttk.Label(
            marco, text="Total por cobrar: $0", font=("", 11, "bold")
        )
        self._lbl_total_saldos.pack(anchor="e")

    # --------------------------------------------------------------- refrescos --

    def refrescar(self) -> None:
        self._refrescar_lista()
        self._refrescar_cuenta()
        self._refrescar_saldos()

    def al_mostrar(self) -> None:
        self.refrescar()

    def _clientes_filtrados(self) -> list[tuple[Cliente, int, date | None]]:
        termino = self._buscar.get().strip().lower()
        estado = self._estado.get()
        filas = []
        for cliente in self._repo.listar():
            if estado == "Activos" and not cliente.activo:
                continue
            if estado == "Inactivos" and cliente.activo:
                continue
            if termino and termino not in cliente.nombre.lower():
                continue
            movs = self._repo.movimientos(cliente.id)
            filas.append((cliente, saldo_de(movs), ultimo_consumo(movs)))
        if self._orden.get() == "Nombre":
            filas.sort(key=lambda f: f[0].nombre.lower())
        else:
            filas.sort(key=lambda f: -f[1])
        return filas

    def _refrescar_lista(self) -> None:
        self._tabla_lista.delete(*self._tabla_lista.get_children())
        for posicion, (cliente, saldo, ultimo) in enumerate(self._clientes_filtrados(), start=1):
            self._tabla_lista.insert(
                "",
                "end",
                iid=str(cliente.id),
                values=(
                    posicion,
                    cliente.nombre,
                    cliente.contacto,
                    _fecha(ultimo),
                    formatear_clp(saldo),
                    "Activo" if cliente.activo else "Inactivo",
                ),
            )

    def _refrescar_cuenta(self) -> None:
        self._tabla_cuenta.delete(*self._tabla_cuenta.get_children())
        self._tabla_estado.delete(*self._tabla_estado.get_children())
        cliente = self._repo.obtener(self._cliente_id) if self._cliente_id else None
        if cliente is None:
            return
        movs = self._repo.movimientos(cliente.id)
        anio, mes = _ciclo_de(self._ciclo.get())
        self._lbl_cliente.config(text=f"{cliente.nombre} · {cliente.contacto}")
        self._lbl_saldo.config(text=f"Saldo actual: {formatear_clp(saldo_de(movs))}")
        corrido = saldo_anterior(movs, anio, mes)
        self._tabla_cuenta.insert(
            "",
            "end",
            values=(
                f"01-{mes:02d}-{anio}",
                "Saldo anterior",
                "Cierre del ciclo anterior",
                "",
                "",
                formatear_clp(corrido),
            ),
        )
        ciclo = [m for m in movs if en_ciclo(m, anio, mes)]
        for m in ciclo:
            corrido += m.efecto
            es_consumo = m.tipo is TipoMovimientoCliente.CONSUMO
            self._tabla_cuenta.insert(
                "",
                "end",
                values=(
                    _fecha(m.fecha),
                    "Consumo"
                    if es_consumo
                    else ("Descuento" if m.medio == MEDIO_DESCUENTO else "Abono"),
                    m.detalle,
                    formatear_clp(m.monto) if es_consumo else "",
                    "" if es_consumo else formatear_clp(m.monto),
                    formatear_clp(corrido),
                ),
            )
            if es_consumo:
                for linea in self._lineas_de(m):  # CL-02: tambien en la pestaña Cuenta
                    self._tabla_cuenta.insert(
                        "",
                        "end",
                        tags=("linea",),
                        values=(
                            "",
                            "",
                            f"      {formatear_cantidad(linea.cantidad)} × {linea.nombre}",
                            formatear_clp(linea.monto),
                            "",
                            "",
                        ),
                    )
        self._lbl_estado.config(text=f"{cliente.nombre} · ciclo de {self._ciclo.get()}")
        for m in ciclo:
            if m.tipo is not TipoMovimientoCliente.CONSUMO:
                continue
            self._tabla_estado.insert(
                "", "end", values=(_fecha(m.fecha), m.detalle, formatear_clp(m.monto))
            )
            for linea in self._lineas_de(m):  # CL-02: cada consumo lista sus productos
                self._tabla_estado.insert(
                    "",
                    "end",
                    tags=("linea",),
                    values=(
                        "",
                        f"      {formatear_cantidad(linea.cantidad)} × {linea.nombre}",
                        formatear_clp(linea.monto),
                    ),
                )
        consumos = consumos_del_ciclo(movs, anio, mes)
        abonos = abonos_del_ciclo(movs, anio, mes)
        descuento = descuento_credito(consumos)
        self._lbl_resumen["anterior"].config(text=formatear_clp(saldo_anterior(movs, anio, mes)))
        self._lbl_resumen["consumos"].config(text=formatear_clp(consumos))
        self._lbl_resumen["descuento"].config(text=f"- {formatear_clp(descuento)}")
        self._lbl_resumen["total"].config(text=formatear_clp(total_a_pagar(consumos)))
        self._lbl_resumen["abonos"].config(text=formatear_clp(abonos))
        self._lbl_resumen["final"].config(text=formatear_clp(corrido))

    def _pagar_estado(self) -> None:
        """Asienta el pago del ciclo: abono por transferencia + descuento, y la deuda queda en 0."""
        if self._cliente_id is None:
            messagebox.showinfo("Estado de cuenta", "Elige un cliente en la lista.")
            return
        anio, mes = _ciclo_de(self._ciclo.get())
        try:
            a_pagar, descuento = self._pagador.calcular(self._cliente_id, anio, mes)
        except ErrorDominio as error:
            messagebox.showerror("Estado de cuenta", str(error))
            return
        if not messagebox.askyesno(
            "Registrar pago del estado de cuenta",
            f"Ciclo de {self._ciclo.get()}.\n\n"
            f"Se registra un abono por transferencia de {formatear_clp(a_pagar)} y el descuento "
            f"del crédito familiar de {formatear_clp(descuento)}.\n\n"
            "No se puede deshacer: un error se corrige con otro movimiento. ¿Continuar?",
        ):
            return
        try:
            self._pagador.ejecutar(self._cliente_id, anio, mes)
        except ErrorDominio as error:
            messagebox.showerror("Estado de cuenta", str(error))
            return
        self._refrescar_cuenta()
        self.refrescar()
        messagebox.showinfo("Estado de cuenta", "Pago del estado de cuenta registrado.")

    def _lineas_de(self, movimiento) -> list:
        """Productos de un consumo a credito (vacio si el consumo no viene de una venta)."""
        if not movimiento.venta_uuid:
            return []
        consultar = getattr(self._repo, "lineas_de_consumo", None)
        return consultar(movimiento.venta_uuid) if consultar else []

    def _exportar_estado(self) -> None:
        filas = [self._tabla_estado.item(i, "values") for i in self._tabla_estado.get_children()]
        if not filas:
            messagebox.showinfo("Estado de cuenta", "Elige un cliente con consumos en el ciclo.")
            return
        resumen = [
            (self._rotulos_resumen[clave].cget("text"), "", valor.cget("text"))
            for clave, valor in self._lbl_resumen.items()
        ]
        exportar_con_dialogo(
            "estado-de-cuenta.csv", ("Fecha", "Detalle", "Monto"), [*filas, ("", "", ""), *resumen]
        )

    def _refrescar_saldos(self) -> None:
        self._tabla_saldos.delete(*self._tabla_saldos.get_children())
        anio, mes = _ciclo_de(self._ciclo_saldos.get())
        total = 0
        for cliente in self._repo.listar():
            movs = self._repo.movimientos(cliente.id)
            saldo = saldo_de(movs)
            if not cliente.activo and saldo == 0:
                continue
            total += saldo
            self._tabla_saldos.insert(
                "",
                "end",
                values=(
                    cliente.nombre,
                    _fecha(ultimo_consumo(movs)),
                    formatear_clp(consumos_del_ciclo(movs, anio, mes)),
                    formatear_clp(abonos_del_ciclo(movs, anio, mes)),
                    formatear_clp(saldo),
                ),
            )
        self._lbl_total_saldos.config(text=f"Total por cobrar: {formatear_clp(total)}")

    # ------------------------------------------------------------------ acciones --

    def _cliente_elegido(self) -> int | None:
        seleccion = self._tabla_lista.selection()
        if not seleccion:
            messagebox.showwarning("Clientes", "Elige un cliente de la lista")
            return None
        return int(seleccion[0])

    def _ver_cuenta(self) -> None:
        cliente_id = self._cliente_elegido()
        if cliente_id is None:
            return
        self.mostrar_cuenta(cliente_id)

    def mostrar_cuenta(self, cliente_id: int) -> None:
        self._cliente_id = cliente_id
        self._refrescar_cuenta()
        self._pestanas.select(1)

    def _nuevo_cliente(self) -> None:
        self._dialogo_cliente(None)

    def _modificar_cliente(self) -> None:
        cliente_id = self._cliente_elegido()
        if cliente_id is not None:
            self._dialogo_cliente(self._repo.obtener(cliente_id))

    def _cambiar_estado(self) -> None:
        cliente_id = self._cliente_elegido()
        if cliente_id is None:
            return
        self.cambiar_estado(cliente_id)

    def cambiar_estado(self, cliente_id: int) -> None:
        cliente = self._repo.obtener(cliente_id)
        try:
            self._gestion.cambiar_estado(cliente_id, not cliente.activo)
        except ErrorDominio as error:
            messagebox.showerror("Clientes", str(error))
            return
        self._mensaje.set(
            f"{cliente.nombre} quedó {'inactivo' if cliente.activo else 'activo'}: "
            "su historial se conserva"
        )
        self.refrescar()

    def guardar_cliente(
        self, cliente_id: int | None, nombre: str, telefono: str, correo: str, obs: str
    ) -> bool:
        try:
            if cliente_id is None:
                self._gestion.crear(nombre, telefono, correo, obs)
            else:
                self._gestion.modificar(cliente_id, nombre, telefono, correo, obs)
        except ErrorDominio as error:
            messagebox.showerror("Clientes", str(error))
            return False
        self._mensaje.set(f"Cliente guardado: {nombre.strip()}")
        self.refrescar()
        return True

    def _dialogo_cliente(self, cliente: Cliente | None) -> None:
        ventana = tk.Toplevel(self)
        ventana.title("Cliente con crédito" if cliente is None else "Modificar cliente")
        ventana.transient(self.winfo_toplevel())
        ttk.Label(
            ventana,
            text="Solo familiares, según lo definido por las propietarias",
            foreground="#666",
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4))
        variables = {}
        for fila, (clave, titulo, valor) in enumerate(
            (
                ("nombre", "Nombre (obligatorio)", cliente.nombre if cliente else ""),
                ("telefono", "Teléfono", cliente.telefono if cliente else ""),
                ("correo", "Correo", cliente.correo if cliente else ""),
                ("obs", "Observaciones", cliente.observaciones if cliente else ""),
            ),
            start=1,
        ):
            ttk.Label(ventana, text=titulo).grid(row=fila, column=0, sticky="w", padx=12, pady=4)
            variables[clave] = tk.StringVar(value=valor)
            entrada = ttk.Entry(ventana, textvariable=variables[clave], width=34)
            entrada.grid(row=fila, column=1, padx=12, pady=4)
            if clave == "nombre":
                entrada.focus_set()

        def confirmar(_evento: object = None) -> None:
            if self.guardar_cliente(
                cliente.id if cliente else None,
                variables["nombre"].get(),
                variables["telefono"].get(),
                variables["correo"].get(),
                variables["obs"].get(),
            ):
                ventana.destroy()

        ventana.bind("<Return>", confirmar)  # Enter guarda, Esc cancela
        ventana.bind("<Escape>", lambda _e: ventana.destroy())
        botones = ttk.Frame(ventana)
        botones.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(botones, text="Guardar cliente", command=confirmar).pack(side="left", padx=6)
        ttk.Button(botones, text="Cancelar", command=ventana.destroy).pack(side="left", padx=6)
        ventana.grab_set()

    def _abono_desde_lista(self) -> None:
        cliente_id = self._cliente_elegido()
        if cliente_id is not None:
            self._dialogo_abono(cliente_id)

    def _abono_de_la_cuenta(self) -> None:
        if self._cliente_id is None:
            messagebox.showwarning("Clientes", "Elige un cliente en la lista")
            return
        self._dialogo_abono(self._cliente_id)

    def registrar_abono(
        self, cliente_id: int, monto_texto: str, fecha_texto: str, medio: str
    ) -> bool:
        try:
            monto = parsear_monto(monto_texto)
        except ValueError:
            messagebox.showerror("Abono", "El monto debe ser un número, por ejemplo 20.000")
            return False
        try:
            fecha = datetime.strptime(fecha_texto.strip(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Abono", "La fecha debe ser AAAA-MM-DD")
            return False
        try:
            self._abonar.ejecutar(cliente_id, monto, MEDIOS.get(medio, medio), fecha)
        except ErrorDominio as error:
            messagebox.showerror("Abono", str(error))
            return False
        self._mensaje.set(f"Abono de {formatear_clp(monto)} registrado")
        self.refrescar()
        return True

    def _dialogo_abono(self, cliente_id: int) -> None:
        cliente = self._repo.obtener(cliente_id)
        saldo = saldo_de(self._repo.movimientos(cliente_id))
        ventana = tk.Toplevel(self)
        ventana.title("Registrar abono")
        ventana.transient(self.winfo_toplevel())
        ttk.Label(ventana, text=f"{cliente.nombre} · saldo actual {formatear_clp(saldo)}").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(10, 6)
        )
        monto = tk.StringVar()
        medio = tk.StringVar(value="Transferencia")
        resultante = tk.StringVar(value=f"Saldo resultante: {formatear_clp(saldo)}")
        ttk.Label(ventana, text="Monto").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        entrada = ttk.Entry(ventana, textvariable=monto, width=16)
        entrada.grid(row=1, column=1, padx=12, pady=4, sticky="w")
        entrada.focus_set()
        ttk.Label(ventana, text="Fecha").grid(row=2, column=0, sticky="w", padx=12, pady=4)
        fecha = CampoFecha(ventana, date.today(), width=14)
        fecha.grid(row=2, column=1, padx=12, pady=4, sticky="w")
        ttk.Label(ventana, text="Medio de pago").grid(row=3, column=0, sticky="w", padx=12, pady=4)
        ttk.Combobox(
            ventana, textvariable=medio, values=list(MEDIOS), state="readonly", width=16
        ).grid(row=3, column=1, padx=12, pady=4, sticky="w")
        ttk.Label(ventana, textvariable=resultante, font=("", 11, "bold")).grid(
            row=4, column=0, columnspan=2, pady=6
        )

        def recalcular(*_a: object) -> None:
            try:
                valor = parsear_monto(monto.get()) if monto.get().strip() else 0
            except ValueError:
                valor = 0
            resultante.set(f"Saldo resultante: {formatear_clp(saldo - valor)}")

        monto.trace_add("write", recalcular)

        def confirmar(_evento: object = None) -> None:
            if self.registrar_abono(cliente_id, monto.get(), fecha.get(), medio.get()):
                ventana.destroy()

        ventana.bind("<Return>", confirmar)  # Enter registra, Esc cancela
        ventana.bind("<Escape>", lambda _e: ventana.destroy())
        botones = ttk.Frame(ventana)
        botones.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(botones, text="Registrar abono", command=confirmar).pack(side="left", padx=6)
        ttk.Button(botones, text="Cancelar", command=ventana.destroy).pack(side="left", padx=6)
        ventana.grab_set()
