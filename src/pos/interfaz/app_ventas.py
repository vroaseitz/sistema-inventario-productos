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

import unicodedata
from decimal import Decimal, InvalidOperation
from tkinter import Listbox, StringVar, Tk, Toplevel, messagebox, ttk

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.casos_uso.sincronizar_pendientes import SincronizarPendientes
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    PublicadorRemoto,
    RepositorioProductos,
    RepositorioTurnosCaja,
    RepositorioVentas,
)
from pos.dominio.caja import TipoMovimientoCaja
from pos.dominio.errores import ErrorDominio
from pos.dominio.pagos import DENOMINACIONES_CLP, ConteoDenominaciones, MedioPago, Pago
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import EstadoVenta, Venta

USUARIO_DEMO = 1  # sin login todavia (ver docs/04-requisitos-no-funcionales)

# Motivos validados por la Product Owner el 22-09 (HU-CAJ-04, hallazgo E-03).
MOTIVOS_MOVIMIENTO_CAJA = (
    "Ingreso de sencillo",
    "Retiro planificado para deposito bancario",
    "Retiro por resguardo durante la jornada",
    "Propinas en fechas especiales",
)

NOMBRES_MEDIO_PAGO = {
    MedioPago.EFECTIVO: "Efectivo",
    MedioPago.TARJETA: "Tarjeta",
    MedioPago.TRANSFERENCIA: "Transferencia",
    MedioPago.CREDITO_CLIENTE: "Credito cliente",
}


def _formatear_clp(monto: int) -> str:
    """Formatea un entero CLP con punto de miles (hallazgo D-10): $26.074."""
    return f"${monto:,}".replace(",", ".")


def _normalizar(texto: str) -> str:
    """Minusculas y sin tildes, para buscar sin que el acento importe (D-26)."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.lower()


class VentanaVentas(Tk):
    def __init__(
        self,
        repositorio_turnos: RepositorioTurnosCaja,
        repositorio_productos: RepositorioProductos,
        repositorio_ventas: RepositorioVentas,
        registrar_venta: RegistrarVenta,
        abrir_turno: AbrirTurnoCaja,
        cerrar_turno: CerrarTurnoCaja,
        registrar_movimiento: RegistrarMovimientoCaja,
        cola: ColaSincronizacion | None = None,
        publicador: PublicadorRemoto | None = None,
    ) -> None:
        super().__init__()
        self._cola = cola
        self._publicador = publicador
        self._repo_turnos = repositorio_turnos
        self._repo_productos = repositorio_productos
        self._repo_ventas = repositorio_ventas
        self._registrar_venta = registrar_venta
        self._abrir_turno = abrir_turno
        self._cerrar_turno = cerrar_turno
        self._registrar_movimiento = registrar_movimiento

        self._venta: Venta | None = None

        self.title("NaturalSur - Venta y Caja")
        self.geometry("980x680")
        self.minsize(900, 620)
        self._construir()
        self._refrescar_turno()
        self._refrescar_sync()
        self._nueva_venta(forzar=True)  # D-01a: siempre hay una venta abierta

    # ------------------------------------------------------------------ UI --

    def _construir(self) -> None:
        marco_turno = ttk.LabelFrame(self, text="Turno de caja")
        marco_turno.pack(fill="x", padx=12, pady=8)

        self._lbl_turno = ttk.Label(marco_turno, text="Sin turno abierto")
        self._lbl_turno.pack(side="left", padx=8, pady=6)

        ttk.Button(marco_turno, text="Abrir turno", command=self._abrir_turno_ui).pack(
            side="right", padx=4, pady=6
        )
        ttk.Button(marco_turno, text="Movimiento de caja", command=self._movimiento_ui).pack(
            side="right", padx=4, pady=6
        )
        ttk.Button(marco_turno, text="Cerrar turno (arqueo)", command=self._cerrar_turno_ui).pack(
            side="right", padx=4, pady=6
        )
        ttk.Button(marco_turno, text="Ver ventas del turno", command=self._ver_ventas_turno).pack(
            side="right", padx=4, pady=6
        )
        # HU-VTA-07: la pantalla indica de forma visible si hay operaciones pendientes.
        # Va en su propia fila: en la barra del turno ya no cabe sin cortarse.
        fila_sync = ttk.Frame(self)
        fila_sync.pack(fill="x", padx=12)
        ttk.Button(fila_sync, text="Sincronizar", command=self._sincronizar).pack(
            side="right", padx=4
        )
        self._lbl_sync = ttk.Label(fila_sync, text="")
        self._lbl_sync.pack(side="right", padx=8)

        marco_venta = ttk.LabelFrame(self, text="Venta en curso")
        marco_venta.pack(fill="x", padx=12, pady=8)

        ttk.Label(marco_venta, text="Codigo").grid(row=0, column=0, padx=4, pady=6)
        self._entrada_codigo = ttk.Entry(marco_venta, width=14)
        self._entrada_codigo.grid(row=0, column=1, padx=4, pady=6)
        self._entrada_codigo.bind("<Return>", lambda _e: self._agregar_producto())  # D-03

        ttk.Label(marco_venta, text="Cantidad").grid(row=0, column=2, padx=4, pady=6)
        self._entrada_cantidad = ttk.Entry(marco_venta, width=8)
        self._entrada_cantidad.insert(0, "1")
        self._entrada_cantidad.grid(row=0, column=3, padx=4, pady=6)
        self._entrada_cantidad.bind("<Return>", lambda _e: self._agregar_producto())

        ttk.Button(marco_venta, text="Agregar", command=self._agregar_producto).grid(
            row=0, column=4, padx=8, pady=6
        )
        ttk.Button(marco_venta, text="Buscar producto", command=self._buscar_producto_ui).grid(
            row=0, column=5, padx=4, pady=6
        )
        ttk.Button(marco_venta, text="Quitar linea", command=self._quitar_linea).grid(
            row=0, column=6, padx=4, pady=6
        )
        ttk.Button(marco_venta, text="Nueva venta", command=self._nueva_venta).grid(
            row=0, column=7, padx=4, pady=6
        )

        columnas = ("codigo", "nombre", "cantidad", "precio", "subtotal")
        anchos = {"codigo": 90, "nombre": 260, "cantidad": 90, "precio": 110, "subtotal": 120}
        self._tabla = ttk.Treeview(self, columns=columnas, show="headings", height=8)
        for col, titulo in zip(
            columnas, ("Codigo", "Nombre", "Cantidad", "Precio", "Subtotal"), strict=True
        ):
            self._tabla.heading(col, text=titulo)
            self._tabla.column(col, width=anchos[col], anchor="w")
        self._tabla.pack(fill="both", expand=True, padx=12, pady=4)
        self._tabla.bind("<Delete>", lambda _e: self._quitar_linea())
        self._tabla.bind("<BackSpace>", lambda _e: self._quitar_linea())

        # D-15: el numero grande es lo que hay que cobrar (ya redondeado si hay
        # efectivo), no el total crudo. La barra de abajo deja el resto siempre
        # visible, no solo en un mensaje que se cierra.
        self._lbl_a_cobrar = ttk.Label(
            self, text="A cobrar: $0", font=("TkDefaultFont", 16, "bold")
        )
        self._lbl_a_cobrar.pack(anchor="e", padx=16)
        self._lbl_resumen = ttk.Label(self, text="Total: $0  ·  Pagado: $0  ·  Vuelto: $0")
        self._lbl_resumen.pack(anchor="e", padx=16)

        marco_pago = ttk.LabelFrame(self, text="Pago")
        marco_pago.pack(fill="both", padx=12, pady=8)

        fila_pago = ttk.Frame(marco_pago)
        fila_pago.pack(fill="x")

        self._medio = StringVar(value=MedioPago.EFECTIVO.value)
        ttk.Combobox(
            fila_pago,
            textvariable=self._medio,
            values=[m.value for m in MedioPago],
            width=16,
            state="readonly",
        ).grid(row=0, column=0, padx=4, pady=6)

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
        ttk.Button(fila_pago, text="Cobrar y cerrar venta", command=self._cerrar_venta).grid(
            row=0, column=5, padx=8, pady=6
        )

        # D-18a: los pagos ya agregados quedan listados y se pueden quitar.
        self._lista_pagos = Listbox(marco_pago, height=3)
        self._lista_pagos.pack(fill="x", padx=4, pady=(0, 6))

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

    def _sincronizar(self) -> None:
        if self._cola is None or self._publicador is None:
            messagebox.showwarning(
                "Sincronizacion", "No hay Supabase configurado (variable SUPABASE_DB_URL)"
            )
            return
        resultado = SincronizarPendientes(self._cola, self._publicador).ejecutar()
        self._refrescar_sync()
        if resultado.fallo_en is not None:
            messagebox.showwarning(
                "Sincronizacion",
                f"Se sincronizaron {resultado.sincronizadas} operaciones y luego se corto "
                "(sin conexion o error del servidor). Lo pendiente se reintenta despues; "
                "no se pierde nada.",
            )

    # -------------------------------------------------------------- Turno --

    def _refrescar_turno(self) -> None:
        turno = self._repo_turnos.obtener_abierto()
        if turno is None:
            self._lbl_turno.config(text="Sin turno abierto")
        else:
            self._lbl_turno.config(
                text=f"Turno #{turno.id} abierto - fondo inicial "
                f"{_formatear_clp(turno.fondo_inicial.monto)}"
            )

    def _contar_denominaciones_ui(self, titulo: str) -> ConteoDenominaciones | None:
        """Dialogo de conteo por billete/moneda (HU-CAJ-01/02, hallazgo E-06).

        Devuelve `None` si se cancela; un `ConteoDenominaciones` (incluso vacio,
        total $0) si se confirma.
        """
        dialogo = Toplevel(self)
        dialogo.title(titulo)
        dialogo.transient(self)
        dialogo.grab_set()

        entradas: dict[int, ttk.Entry] = {}
        for fila, denominacion in enumerate(DENOMINACIONES_CLP):
            ttk.Label(dialogo, text=_formatear_clp(denominacion)).grid(
                row=fila, column=0, padx=8, pady=3, sticky="w"
            )
            entrada = ttk.Entry(dialogo, width=8)
            entrada.insert(0, "0")
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
        conteo = self._contar_denominaciones_ui("Abrir turno - contar fondo inicial")
        if conteo is None:
            return
        try:
            self._abrir_turno.ejecutar(
                usuario_id=USUARIO_DEMO,
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

    def _cerrar_turno_ui(self) -> None:
        conteo = self._contar_denominaciones_ui("Cerrar turno - contar efectivo")
        if conteo is None:
            return
        try:
            arqueo = self._cerrar_turno.ejecutar(efectivo_contado=Dinero(conteo.total))
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo cerrar el turno", str(exc))
            return
        detalle = "\n".join(
            f"{NOMBRES_MEDIO_PAGO[medio]}: {_formatear_clp(monto.monto)}"
            for medio, monto in arqueo.totales_por_medio.items()
        )
        messagebox.showinfo(
            "Arqueo de cierre",
            f"{detalle}\n\n"
            f"Efectivo esperado: {_formatear_clp(arqueo.efectivo_esperado)}\n"
            f"Efectivo contado: {_formatear_clp(arqueo.efectivo_contado.monto)}\n"
            f"Diferencia: {_formatear_clp(arqueo.diferencia)}",
        )
        self._refrescar_turno()

    def _movimiento_ui(self) -> None:
        # E-03: un solo dialogo con tipo, motivo de una lista, observacion y monto,
        # en vez de tres ventanas sucesivas con motivo en texto libre.
        dialogo = Toplevel(self)
        dialogo.title("Movimiento de caja")
        dialogo.transient(self)
        dialogo.grab_set()

        ttk.Label(dialogo, text="Tipo").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        tipo_var = StringVar(value=TipoMovimientoCaja.RETIRO.value)
        ttk.Combobox(
            dialogo,
            textvariable=tipo_var,
            values=[t.value for t in TipoMovimientoCaja],
            state="readonly",
            width=20,
        ).grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(dialogo, text="Motivo").grid(row=1, column=0, padx=8, pady=6, sticky="w")
        motivo_var = StringVar(value=MOTIVOS_MOVIMIENTO_CAJA[0])
        ttk.Combobox(
            dialogo, textvariable=motivo_var, values=MOTIVOS_MOVIMIENTO_CAJA, width=36
        ).grid(row=1, column=1, padx=8, pady=6)

        ttk.Label(dialogo, text="Observacion").grid(row=2, column=0, padx=8, pady=6, sticky="w")
        entrada_obs = ttk.Entry(dialogo, width=38)
        entrada_obs.grid(row=2, column=1, padx=8, pady=6)

        ttk.Label(dialogo, text="Monto (CLP)").grid(row=3, column=0, padx=8, pady=6, sticky="w")
        entrada_monto = ttk.Entry(dialogo, width=16)
        entrada_monto.grid(row=3, column=1, padx=8, pady=6)

        def confirmar() -> None:
            try:
                monto = int(entrada_monto.get().strip())
                if monto <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Monto invalido", "El monto debe ser un entero mayor a cero")
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
            messagebox.showinfo(
                "Movimiento registrado",
                f"{tipo_var.get().capitalize()} de {_formatear_clp(monto)} registrado",
            )

        ttk.Button(dialogo, text="Registrar", command=confirmar).grid(
            row=4, column=0, columnspan=2, pady=10
        )

    def _ver_ventas_turno(self) -> None:
        # E-08: poder ver la venta de la jornada sin tener que cerrar el turno.
        turno = self._repo_turnos.obtener_abierto()
        if turno is None:
            messagebox.showwarning("Sin turno", "No hay un turno de caja abierto")
            return
        ventas = [
            v
            for v in self._repo_ventas.obtener_por_turno(turno.id)
            if v.estado is EstadoVenta.PAGADA
        ]
        totales: dict[MedioPago, int] = dict.fromkeys(MedioPago, 0)
        for venta in ventas:
            for pago in venta.pagos:
                totales[pago.medio] += pago.monto.monto
        detalle = "\n".join(
            f"{NOMBRES_MEDIO_PAGO[medio]}: {_formatear_clp(monto)}"
            for medio, monto in totales.items()
        )
        total_general = sum(totales.values())
        messagebox.showinfo(
            "Ventas del turno",
            f"{len(ventas)} venta(s) registrada(s)\n\n{detalle}\n\n"
            f"Total: {_formatear_clp(total_general)}",
        )

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
            self._venta = self._registrar_venta.iniciar(usuario_id=USUARIO_DEMO)
        except ErrorDominio as exc:
            self._venta = None
            if not forzar:
                messagebox.showerror("No se pudo iniciar la venta", str(exc))
        self._entrada_cantidad.delete(0, "end")
        self._entrada_cantidad.insert(0, "1")
        self._refrescar_ticket()
        self._entrada_codigo.focus_set()

    def _venta_actual(self) -> Venta | None:
        if self._venta is None:
            messagebox.showwarning("Sin venta", "Primero inicia una venta nueva")
        return self._venta

    def _agregar_producto(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        codigo = self._entrada_codigo.get().strip()
        if not codigo:
            return
        try:
            # D-07: la Product Owner pidio aceptar coma y punto como separador.
            texto_cantidad = self._entrada_cantidad.get().strip().replace(",", ".")
            cantidad = Decimal(texto_cantidad or "1")
        except InvalidOperation:
            messagebox.showerror("Cantidad invalida", "La cantidad debe ser un numero")
            return
        try:
            self._registrar_venta.agregar_producto(venta, codigo, cantidad)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo agregar el producto", str(exc))
            return
        self._entrada_codigo.delete(0, "end")
        self._entrada_cantidad.delete(0, "end")
        self._entrada_cantidad.insert(0, "1")  # D-23
        self._refrescar_ticket()
        self._entrada_codigo.focus_set()  # D-24

    def _quitar_linea(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        seleccion = self._tabla.selection()
        if not seleccion:
            messagebox.showwarning("Sin seleccion", "Selecciona una linea del ticket")
            return
        codigo = self._tabla.item(seleccion[0], "values")[0]
        try:
            venta.quitar_detalle(codigo)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo quitar la linea", str(exc))
            return
        self._refrescar_ticket()

    def _buscar_producto_ui(self) -> None:
        # D-26: encontrar un producto por nombre cuando no tiene codigo de barras
        # o el lector no lo lee, sin distinguir tildes ni mayusculas.
        dialogo = Toplevel(self)
        dialogo.title("Buscar producto")
        dialogo.transient(self)
        dialogo.grab_set()
        dialogo.geometry("360x320")

        ttk.Label(dialogo, text="Nombre").pack(padx=8, pady=(8, 2), anchor="w")
        entrada = ttk.Entry(dialogo, width=40)
        entrada.pack(padx=8, pady=2)
        entrada.focus_set()

        lista = Listbox(dialogo, width=50, height=12)
        lista.pack(padx=8, pady=8, fill="both", expand=True)

        productos = self._repo_productos.listar()

        def refrescar_lista(*_args: object) -> None:
            termino = _normalizar(entrada.get().strip())
            lista.delete(0, "end")
            for producto in productos:
                if termino in _normalizar(producto.nombre):
                    lista.insert("end", f"{producto.codigo} - {producto.nombre}")

        def elegir(_evento: object = None) -> None:
            seleccion = lista.curselection()
            if not seleccion:
                return
            codigo = lista.get(seleccion[0]).split(" - ", 1)[0]
            self._entrada_codigo.delete(0, "end")
            self._entrada_codigo.insert(0, codigo)
            dialogo.destroy()
            self._entrada_cantidad.focus_set()

        entrada.bind("<KeyRelease>", refrescar_lista)
        lista.bind("<Double-Button-1>", elegir)
        refrescar_lista()

        ttk.Button(dialogo, text="Seleccionar", command=elegir).pack(pady=(0, 8))

    def _refrescar_ticket(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        venta = self._venta
        self._lista_pagos.delete(0, "end")

        if venta is None:
            self._lbl_a_cobrar.config(text="A cobrar: $0")
            self._lbl_resumen.config(text="Total: $0  ·  Pagado: $0  ·  Vuelto: $0")
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
                    detalle.cantidad,
                    _formatear_clp(detalle.precio_unitario.monto),
                    _formatear_clp(detalle.subtotal.monto),
                ),
            )

        for indice, pago in enumerate(venta.pagos):
            self._lista_pagos.insert(
                "end",
                f"{indice + 1}. {NOMBRES_MEDIO_PAGO[pago.medio]}: "
                f"{_formatear_clp(pago.monto.monto)}",
            )

        a_cobrar = venta.total_a_cobrar.monto
        pagado = venta.total_pagado.monto
        self._lbl_a_cobrar.config(text=f"A cobrar: {_formatear_clp(a_cobrar)}")
        self._lbl_resumen.config(
            text=f"Total: {_formatear_clp(venta.total.monto)}  ·  "
            f"Pagado: {_formatear_clp(pagado)}  ·  "
            f"Vuelto: {_formatear_clp(venta.vuelto_entregado.monto)}"
        )

        # D-19: proponer el saldo pendiente como monto por defecto; la cajera
        # solo lo cambia si es un pago parcial.
        saldo = max(0, a_cobrar - pagado)
        self._entrada_monto_pago.delete(0, "end")
        if saldo:
            self._entrada_monto_pago.insert(0, str(saldo))

    def _agregar_pago(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        try:
            monto = int(self._entrada_monto_pago.get().strip())
        except ValueError:
            messagebox.showerror("Monto invalido", "El monto debe ser un numero entero")
            return
        if monto <= 0:  # F-04
            messagebox.showerror("Monto invalido", "El monto debe ser mayor que cero")
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
                    messagebox.showinfo("Vuelto", f"Vuelto: {vuelto_fmt}")
            else:
                pago = Pago(medio=medio, monto=Dinero(monto))
            self._registrar_venta.agregar_pago(venta, pago)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo agregar el pago", str(exc))
            return
        self._refrescar_ticket()

    def _quitar_pago(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        seleccion = self._lista_pagos.curselection()
        if not seleccion:
            messagebox.showwarning("Sin seleccion", "Selecciona un pago de la lista")
            return
        try:
            venta.quitar_pago(seleccion[0])
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo quitar el pago", str(exc))
            return
        self._refrescar_ticket()

    def _cerrar_venta(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        try:
            self._registrar_venta.cerrar(venta)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo cerrar la venta", str(exc))
            return
        messagebox.showinfo("Venta cerrada", f"Venta #{venta.id} registrada con exito")
        self._refrescar_sync()
        self._nueva_venta(forzar=True)  # D-01a: queda lista para la siguiente


def main() -> None:
    from pos.infraestructura.config import Config
    from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
    from pos.infraestructura.sqlite.conexion import crear_conexion
    from pos.infraestructura.sqlite.esquema import crear_esquema
    from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
    from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
    from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
    from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite
    from pos.infraestructura.supabase.adaptador_supabase import AdaptadorSupabase

    config = Config.desde_entorno()
    conexion = crear_conexion(config.sqlite_path)
    crear_esquema(conexion)

    repo_productos = RepositorioProductosSQLite(conexion)
    repo_existencias = RepositorioExistenciasSQLite(conexion)
    repo_turnos = RepositorioTurnosCajaSQLite(conexion)
    repo_ventas = RepositorioVentasSQLite(conexion)
    cola = ColaSincronizacionSQLite(conexion)
    publicador = AdaptadorSupabase(config.supabase_db_url) if config.supabase_db_url else None

    registrar_venta = RegistrarVenta(
        repo_ventas, repo_turnos, repo_productos, repo_existencias, cola=cola
    )
    abrir_turno = AbrirTurnoCaja(repo_turnos, cola=cola)
    cerrar_turno = CerrarTurnoCaja(repo_turnos, repo_ventas, cola=cola)
    registrar_movimiento = RegistrarMovimientoCaja(repo_turnos, cola=cola)

    VentanaVentas(
        repo_turnos,
        repo_productos,
        repo_ventas,
        registrar_venta,
        abrir_turno,
        cerrar_turno,
        registrar_movimiento,
        cola=cola,
        publicador=publicador,
    ).mainloop()


if __name__ == "__main__":
    main()
