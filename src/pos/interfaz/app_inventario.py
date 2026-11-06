"""Pantalla F3 Inventario: entrada de stock con vencimiento y alertas con descuento sugerido.

Cubre HU-INV-01/02 (ingreso con lote) y HU-INV-03/06 (alerta de vencimiento con descuento
sugerido). La politica de descuento es una propuesta pendiente de validar con la PO.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento
from pos.aplicacion.casos_uso.consultar_inventario import (
    ConsultarExistencias,
    ConsultarMovimientos,
    DefinirStockMinimo,
    ReporteInventario,
)
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.casos_uso.registrar_merma import RegistrarMerma
from pos.aplicacion.puertos import (
    RepositorioCategorias,
    RepositorioExistencias,
    RepositorioLotes,
    RepositorioProductos,
)
from pos.dominio.errores import ErrorDominio
from pos.dominio.inventario import MotivoAjuste
from pos.interfaz.app_inventario_consultas import (
    PanelExistencias,
    PanelMovimientos,
    PanelReporteInventario,
)
from pos.interfaz.campo_fecha import CampoFecha
from pos.interfaz.sesion import Sesion
from pos.interfaz.tema import MODULOS_COLOR, PAPEL, BotonAccion


def _clp(monto: int) -> str:
    return "$" + f"{monto:,}".replace(",", ".")


# HU-INV-04: motivos del prototipo v3 (la lista final la define la PO con las propietarias).
MOTIVOS_MERMA = {
    "Vencimiento": MotivoAjuste.VENCIMIENTO,
    "Rotura": MotivoAjuste.ROTURA,
    "Pérdida": MotivoAjuste.PERDIDA,
    "Consumo interno": MotivoAjuste.CONSUMO_INTERNO,
    "Devolución": MotivoAjuste.DEVOLUCION,
}


class PanelEntradaYAlertas:
    """Entrada de stock y merma (ventanas modales) + pestañas Lotes y Alertas del prototipo."""

    al_cambiar = None  # la ventana lo fija para refrescar todas las pestañas

    def __init__(
        self,
        parent: ttk.Notebook,
        repo_productos: RepositorioProductos,
        ingresar_stock: IngresarStock,
        consultar_alertas: ConsultarAlertasVencimiento,
        repo_lotes: RepositorioLotes | None = None,
        registrar_merma: RegistrarMerma | None = None,
        repo_existencias: RepositorioExistencias | None = None,
        sesion: Sesion | None = None,
    ) -> None:
        self._parent = parent
        self._productos = repo_productos
        self._ingresar = ingresar_stock
        self._alertas = consultar_alertas
        self._repo_lotes = repo_lotes
        self._merma = registrar_merma
        self._existencias = repo_existencias
        self._sesion = sesion or Sesion()

        self._codigo = tk.StringVar(master=parent)
        self._cantidad = tk.StringVar(master=parent)
        self._codigo_lote = tk.StringVar(master=parent)  # I-02: codigo impreso en el envase
        self._motivo = tk.StringVar(master=parent, value="Compra a proveedor")
        self._mensaje = tk.StringVar(master=parent)

        self.marco_lotes = ttk.Frame(parent, padding=8)
        self.marco_alertas = ttk.Frame(parent, padding=8)
        self._construir_entrada()
        if self._merma is not None:
            self._construir_merma()

        ttk.Label(
            self.marco_alertas,
            text="Lotes que vencen pronto, con el descuento que se sugiere para venderlos antes.",
            foreground="#666",
        ).pack(anchor="w")
        columnas = ("producto", "vence", "dias", "saldo", "precio", "descuento", "sugerido")
        self._tabla = ttk.Treeview(self.marco_alertas, columns=columnas, show="headings", height=14)
        for clave, titulo, ancho in (
            ("producto", "Producto", 260),
            ("vence", "Vence", 100),
            ("dias", "Días", 70),
            ("saldo", "Saldo", 70),
            ("precio", "Precio", 90),
            ("descuento", "Descuento", 90),
            ("sugerido", "Precio sugerido", 130),
        ):
            self._tabla.heading(clave, text=titulo)
            self._tabla.column(clave, width=ancho, anchor="w")
        self._tabla.tag_configure("vencido", foreground="#a11")
        self._tabla.pack(fill="both", expand=True, pady=4)
        ttk.Label(
            self.marco_alertas,
            text="El descuento es una sugerencia (politica propuesta); no modifica el precio.",
            foreground="#666",
        ).pack(anchor="w")
        self._tabla_lotes = None
        if self._repo_lotes is not None:
            self._tabla_lotes = ttk.Treeview(
                self.marco_lotes,
                columns=("lote", "producto", "vence", "saldo"),
                show="headings",
                height=14,
            )
            for clave, titulo, ancho in (
                ("lote", "Lote", 100),
                ("producto", "Producto", 320),
                ("vence", "Vence", 120),
                ("saldo", "Saldo", 90),
            ):
                self._tabla_lotes.heading(clave, text=titulo)
                self._tabla_lotes.column(clave, width=ancho, anchor="w")
            self._tabla_lotes.pack(fill="both", expand=True)
        self.refrescar()

    # ------------------------------------------------------------------ ventanas modales --

    def _modal(self, titulo: str) -> tk.Toplevel:
        """Ventana oculta que se muestra con `abrir_*`; los campos existen siempre."""
        raiz = self._parent.winfo_toplevel()
        ventana = tk.Toplevel(raiz)
        ventana.title(titulo)
        ventana.transient(raiz)
        ventana.withdraw()
        ventana.protocol("WM_DELETE_WINDOW", ventana.withdraw)
        ventana.bind("<Escape>", lambda _e: ventana.withdraw())
        return ventana

    @staticmethod
    def _mostrar(ventana: tk.Toplevel) -> None:
        ventana.deiconify()
        ventana.lift()
        ventana.focus_force()

    def abrir_entrada(self) -> None:
        self._limpiar_entrada()  # I-05: el cuadro siempre se abre vacio
        self._mostrar(self.dlg_entrada)

    def _limpiar_entrada(self) -> None:
        """Deja el cuadro de ingreso como nuevo: sin el codigo ni la cantidad de la vez anterior
        (se podia ingresar stock al producto equivocado sin darse cuenta)."""
        self._codigo.set("")
        self._cantidad.set("")
        self._codigo_lote.set("")
        self._vence.set("")
        self._motivo.set("Compra a proveedor")

    def hay_dialogo_abierto(self) -> bool:
        return any(
            d.winfo_viewable() for d in (self.dlg_entrada, getattr(self, "dlg_merma", None)) if d
        )

    def abrir_merma(self) -> None:
        if self._merma is not None:
            self._mostrar(self.dlg_merma)

    def _construir_entrada(self) -> None:
        self.dlg_entrada = self._modal("Agregar a inventario")
        marco = ttk.Frame(self.dlg_entrada, padding=14)
        marco.pack(fill="both", expand=True)
        # R-01: "Vence" tiene calendario desplegable (tambien se puede escribir AAAA-MM-DD).
        self._vence = CampoFecha(marco, width=14)
        campos = (
            ("Código de producto", self._codigo),
            ("Cantidad", self._cantidad),
            ("Vence (calendario o AAAA-MM-DD)", self._vence),
            ("Código de lote (impreso)", self._codigo_lote),
            ("Motivo", self._motivo),
        )
        for fila, (etiqueta, variable) in enumerate(campos):
            ttk.Label(marco, text=etiqueta).grid(row=fila, column=0, sticky="w", padx=4, pady=4)
            if variable is self._vence:
                self._vence.grid(row=fila, column=1, padx=4, sticky="w")
                continue
            entrada = ttk.Entry(marco, textvariable=variable, width=28)
            entrada.grid(row=fila, column=1, padx=4)
            entrada.bind("<Return>", lambda _e: self._registrar())
        botones = ttk.Frame(marco)
        botones.grid(row=len(campos), column=0, columnspan=2, pady=(12, 0))
        ttk.Button(
            botones, text="Ingresar", style="Primario.TButton", command=self._registrar
        ).pack(side="left", padx=6)
        ttk.Button(botones, text="Cerrar", command=self.dlg_entrada.withdraw).pack(side="left")

    # ------------------------------------------- Registrar merma o ajuste (HU-INV-04) --

    def _construir_merma(self) -> None:
        self.dlg_merma = self._modal("Ajustes y mermas")
        marco = ttk.Frame(self.dlg_merma, padding=14)
        marco.pack(fill="both", expand=True)
        self._merma_codigo = tk.StringVar()
        self._merma_cantidad = tk.StringVar()
        self._merma_motivo = tk.StringVar()
        self._merma_obs = tk.StringVar()
        self._merma_estado = tk.StringVar(value="Existencia actual: -  ·  Resultante: -")
        campos = (
            ("Código de producto", ttk.Entry(marco, textvariable=self._merma_codigo, width=28)),
            (
                "Cantidad a dar de baja",
                ttk.Entry(marco, textvariable=self._merma_cantidad, width=14),
            ),
            (
                "Motivo (obligatorio)",
                ttk.Combobox(
                    marco,
                    textvariable=self._merma_motivo,
                    values=list(MOTIVOS_MERMA),
                    state="readonly",
                    width=26,
                ),
            ),
            ("Observacion", ttk.Entry(marco, textvariable=self._merma_obs, width=34)),
        )
        for fila, (titulo, widget) in enumerate(campos):
            ttk.Label(marco, text=titulo).grid(row=fila, column=0, sticky="w", padx=4, pady=4)
            widget.grid(row=fila, column=1, padx=4, sticky="w")
        for variable in (self._merma_codigo, self._merma_cantidad):
            variable.trace_add("write", lambda *_a: self._actualizar_estado_merma())
        ttk.Label(marco, textvariable=self._merma_estado, foreground="#666").grid(
            row=len(campos), column=0, columnspan=2, sticky="w", padx=4, pady=(8, 0)
        )
        botones = ttk.Frame(marco)
        botones.grid(row=len(campos) + 1, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(
            botones, text="Registrar merma", style="Primario.TButton", command=self._registrar_merma
        ).pack(side="left", padx=6)
        ttk.Button(botones, text="Cerrar", command=self.dlg_merma.withdraw).pack(side="left")
        for _titulo, widget in campos:
            widget.bind("<Return>", lambda _e: self._registrar_merma())

    def _existencia_actual(self, codigo: str) -> Decimal | None:
        if self._existencias is None or not codigo:
            return None
        existencia = self._existencias.obtener(codigo)
        return existencia.cantidad if existencia is not None else None

    def _actualizar_estado_merma(self) -> None:
        actual = self._existencia_actual(self._merma_codigo.get().strip())
        if actual is None:
            self._merma_estado.set("Existencia actual: -  ·  Resultante: -")
            return
        try:
            baja = Decimal(self._merma_cantidad.get().strip().replace(",", ".") or "0")
        except InvalidOperation:
            baja = Decimal("0")
        self._merma_estado.set(f"Existencia actual: {actual}  ·  Resultante: {actual - baja}")

    def _registrar_merma(self) -> None:
        codigo = self._merma_codigo.get().strip()
        if not codigo:
            messagebox.showerror("Merma", "Falta el código del producto")
            return
        if not self._merma_cantidad.get().strip():
            messagebox.showerror("Merma", "Falta la cantidad a dar de baja")
            return
        motivo = MOTIVOS_MERMA.get(self._merma_motivo.get())
        if motivo is None:
            messagebox.showerror("Merma", "Falta el motivo (es obligatorio)")
            return
        try:
            ajuste = self._merma.ejecutar(
                codigo,
                self._merma_cantidad.get().strip().replace(",", "."),
                motivo,
                self._sesion.nombre or str(self._sesion.usuario_id),
                self._merma_obs.get(),
            )
        except ErrorDominio as error:
            messagebox.showerror("Merma", str(error))
            return
        self._mensaje.set(
            f"Merma registrada: {codigo} −{-ajuste.diferencia_conteo} ({self._merma_motivo.get()})"
        )
        for variable in (self._merma_codigo, self._merma_cantidad, self._merma_obs):
            variable.set("")
        self._merma_motivo.set("")
        self.dlg_merma.withdraw()
        self._tras_cambio()

    def _registrar(self) -> None:
        # I-03: cada dato faltante o mal escrito se nombra en el mensaje.
        codigo = self._codigo.get().strip()
        if not codigo:
            messagebox.showerror("Inventario", "Falta el código del producto")
            return
        texto_cantidad = self._cantidad.get().strip().replace(",", ".")
        if not texto_cantidad:
            messagebox.showerror("Inventario", "Falta la cantidad")
            return
        try:
            cantidad = Decimal(texto_cantidad)
        except InvalidOperation:
            messagebox.showerror("Inventario", "La cantidad debe ser un número, por ejemplo 12")
            return
        if cantidad <= 0:
            messagebox.showerror("Inventario", "La cantidad debe ser mayor que cero")
            return
        if not self._motivo.get().strip():
            messagebox.showerror("Inventario", "Falta el motivo")
            return
        vence = self._vence.get().strip()
        try:
            fecha = datetime.strptime(vence, "%Y-%m-%d").date() if vence else None
        except ValueError:
            messagebox.showerror("Inventario", "La fecha de vencimiento debe ser AAAA-MM-DD")
            return
        try:
            self._ingresar.ejecutar(
                codigo,
                cantidad,
                self._motivo.get(),
                fecha_vencimiento=fecha,
                codigo_lote=self._codigo_lote.get(),
            )
        except ErrorDominio as error:
            messagebox.showerror("Inventario", str(error))
            return
        self._mensaje.set(f"Stock ingresado: {codigo}")
        self._limpiar_entrada()
        self.dlg_entrada.withdraw()
        self._tras_cambio()

    def _tras_cambio(self) -> None:
        """Ingreso o merma hechos: refresca esta pestaña y las demás de la ventana."""
        if self.al_cambiar is not None:
            self.al_cambiar()
        else:
            self.refrescar()

    def al_mostrar(self) -> None:
        """Se llama al entrar a F3: las ventas y productos nuevos cambian las alertas."""
        self.refrescar()

    def _refrescar_lotes(self) -> None:
        """I-02: lotes con saldo por vencimiento, con su codigo de lote."""
        if self._tabla_lotes is None or self._repo_lotes is None:
            return
        self._tabla_lotes.delete(*self._tabla_lotes.get_children())
        for lote in sorted(self._repo_lotes.con_saldo(), key=lambda x: x.fecha_vencimiento):
            producto = self._productos.obtener_por_codigo(lote.codigo_producto)
            self._tabla_lotes.insert(
                "",
                "end",
                values=(
                    lote.etiqueta,
                    producto.nombre if producto else lote.codigo_producto,
                    lote.fecha_vencimiento.isoformat(),
                    lote.saldo,
                ),
            )

    def refrescar(self) -> None:
        self._refrescar_lotes()
        self._tabla.delete(*self._tabla.get_children())
        for alerta in self._alertas.ejecutar(date.today()):
            self._tabla.insert(
                "",
                "end",
                tags=("vencido",) if alerta.vencido else (),
                values=(
                    alerta.nombre_producto,
                    alerta.lote.fecha_vencimiento.isoformat(),
                    "VENCIDO" if alerta.vencido else alerta.dias_restantes,
                    alerta.lote.saldo,
                    _clp(alerta.precio_actual.monto),
                    f"{alerta.descuento_pct}%",
                    _clp(alerta.precio_sugerido.monto),
                ),
            )


class VentanaInventario(ttk.Frame):
    """F3 Inventario: entrada y alertas (HU-INV-01/02/03/04/06), existencias con minimo
    (HU-INV-05), reporte valorizado (HU-INV-07) y movimientos (HU-INV-08)."""

    def __init__(
        self,
        parent: tk.Misc,
        repo_productos: RepositorioProductos,
        ingresar_stock: IngresarStock,
        consultar_alertas: ConsultarAlertasVencimiento,
        repo_lotes: RepositorioLotes | None = None,
        registrar_merma: RegistrarMerma | None = None,
        repo_existencias: RepositorioExistencias | None = None,
        sesion: Sesion | None = None,
        consultar_existencias: ConsultarExistencias | None = None,
        definir_minimo: DefinirStockMinimo | None = None,
        reporte_inventario: ReporteInventario | None = None,
        consultar_movimientos: ConsultarMovimientos | None = None,
        repo_categorias: RepositorioCategorias | None = None,
    ) -> None:
        super().__init__(parent)
        self._color, self._claro = MODULOS_COLOR["F3"]
        barra = tk.Frame(self, bg=PAPEL)
        barra.pack(fill="x", padx=12, pady=(8, 4))
        self._pestanas = ttk.Notebook(self)
        self._panel_entrada = PanelEntradaYAlertas(
            self._pestanas,
            repo_productos,
            ingresar_stock,
            consultar_alertas,
            repo_lotes,
            registrar_merma,
            repo_existencias,
            sesion,
        )
        self._paneles: list = []
        self._panel_entrada.al_cambiar = self.refrescar
        acciones = [
            ("Agregar a inventario", self._panel_entrada.abrir_entrada, "INS", "primario"),
        ]
        if registrar_merma is not None:
            acciones.append(("Ajustes y mermas", self._panel_entrada.abrir_merma, "", "normal"))
        if reporte_inventario is not None:
            acciones.append(("Reporte de inventario", self.abrir_reporte, "", "normal"))
        if consultar_movimientos is not None:
            acciones.append(("Reporte de movimientos", self.abrir_movimientos, "", "normal"))
        for texto, comando, tecla, variante in acciones:
            BotonAccion(
                barra, texto, comando, tecla, variante, color=self._color, fondo=PAPEL
            ).pack(side="left", padx=(0, 6))
        tk.Label(barra, textvariable=self._panel_entrada._mensaje, bg=PAPEL, fg=self._color).pack(
            side="left", padx=10
        )
        self.bind_all("<Insert>", self._atajo_entrada, add="+")  # I-04: el boton dice «INS»
        self._pestanas.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._destinos: dict[str, int] = {}
        if consultar_existencias is not None and definir_minimo is not None:
            self.existencias = PanelExistencias(
                self._pestanas, consultar_existencias, definir_minimo, repo_categorias
            )
            self._destinos["existencias"] = len(self._pestanas.tabs())
            self._pestanas.add(self.existencias, text="Existencias")
            self._paneles.append(self.existencias)
        self._destinos["lotes"] = len(self._pestanas.tabs())
        self._pestanas.add(self._panel_entrada.marco_lotes, text="Lotes y vencimientos")
        self._destinos["alertas"] = len(self._pestanas.tabs())
        self._pestanas.add(self._panel_entrada.marco_alertas, text="Alertas")
        # Los reportes viven en ventanas ocultas que abren los botones de la barra.
        if reporte_inventario is not None:
            self._ventana_reporte, self.reporte = self._modal_con_panel(
                "Reporte de inventario",
                lambda v: PanelReporteInventario(v, reporte_inventario, repo_categorias),
            )
            self._paneles.append(self.reporte)
        if consultar_movimientos is not None:
            self._ventana_movimientos, self.movimientos = self._modal_con_panel(
                "Reporte de movimientos", lambda v: PanelMovimientos(v, consultar_movimientos)
            )
            self._paneles.append(self.movimientos)

    def _modal_con_panel(self, titulo: str, crear) -> tuple[tk.Toplevel, object]:
        ventana = tk.Toplevel(self.winfo_toplevel())
        ventana.title(titulo)
        ventana.transient(self.winfo_toplevel())
        ventana.geometry("1000x560")
        ventana.withdraw()
        ventana.bind("<Escape>", lambda _e: ventana.withdraw())
        ventana.protocol("WM_DELETE_WINDOW", ventana.withdraw)
        panel = crear(ventana)
        panel.pack(fill="both", expand=True, padx=8, pady=8)
        return ventana, panel

    def abrir_reporte(self) -> None:
        self.reporte.refrescar()
        self._ventana_reporte.deiconify()
        self._ventana_reporte.lift()

    def abrir_movimientos(self) -> None:
        self.movimientos.refrescar()
        self._ventana_movimientos.deiconify()
        self._ventana_movimientos.lift()

    def __getattr__(self, nombre: str):
        """La pestana de entrada conserva sus nombres de siempre (_codigo, _registrar, ...)."""
        if nombre.startswith("__") or nombre == "_panel_entrada":
            raise AttributeError(nombre)
        return getattr(self._panel_entrada, nombre)

    def seleccionar_pestana(self, nombre: str) -> None:
        """«alertas» y «existencias» (desde los avisos del resumen del dia)."""
        destino = self._destinos.get(nombre)
        if destino is not None:
            self._pestanas.select(destino)

    def _atajo_entrada(self, _evento=None) -> None:
        """Insert abre «Agregar a inventario» desde esta pantalla (como en F2 y F5)."""
        if self.winfo_ismapped() and not self._panel_entrada.hay_dialogo_abierto():
            self._panel_entrada.abrir_entrada()

    def refrescar(self) -> None:
        self._panel_entrada.refrescar()
        for panel in self._paneles:
            panel.refrescar()

    def al_mostrar(self) -> None:
        self.refrescar()
