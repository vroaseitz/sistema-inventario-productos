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


class PanelEntradaYAlertas(ttk.Frame):
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
    ) -> None:
        super().__init__(parent, padding=12)
        self._productos = repo_productos
        self._ingresar = ingresar_stock
        self._alertas = consultar_alertas
        self._repo_lotes = repo_lotes
        self._merma = registrar_merma
        self._existencias = repo_existencias
        self._sesion = sesion or Sesion()

        self._codigo = tk.StringVar()
        self._cantidad = tk.StringVar()
        self._codigo_lote = tk.StringVar()  # I-02: codigo impreso en el envase
        self._motivo = tk.StringVar(value="Compra a proveedor")
        self._mensaje = tk.StringVar()

        formulario = ttk.LabelFrame(self, text="Entrada de stock", padding=10)
        formulario.pack(fill="x")
        # R-01: "Vence" tiene calendario desplegable (tambien se puede escribir AAAA-MM-DD).
        self._vence = CampoFecha(formulario, width=14)
        campos = (
            ("Codigo de producto", self._codigo),
            ("Cantidad", self._cantidad),
            ("Vence (calendario o AAAA-MM-DD)", self._vence),
            ("Codigo de lote (impreso)", self._codigo_lote),
            ("Motivo", self._motivo),
        )
        for columna, (etiqueta, variable) in enumerate(campos):
            ttk.Label(formulario, text=etiqueta).grid(row=0, column=columna, sticky="w", padx=4)
            if variable is self._vence:
                self._vence.grid(row=1, column=columna, padx=4, pady=(2, 0), sticky="w")
                continue
            ttk.Entry(formulario, textvariable=variable, width=20).grid(
                row=1, column=columna, padx=4, pady=(2, 0)
            )
        ttk.Button(formulario, text="Ingresar", command=self._registrar).grid(
            row=1, column=len(campos), padx=8
        )
        if self._merma is not None:
            self._construir_merma()
        ttk.Label(self, textvariable=self._mensaje, foreground="#5B3E7E").pack(anchor="w", pady=6)

        ttk.Label(self, text="Alertas de vencimiento", font=("TkDefaultFont", 12, "bold")).pack(
            anchor="w"
        )
        columnas = ("producto", "vence", "dias", "saldo", "precio", "descuento", "sugerido")
        self._tabla = ttk.Treeview(self, columns=columnas, show="headings", height=14)
        for clave, titulo, ancho in (
            ("producto", "Producto", 220),
            ("vence", "Vence", 100),
            ("dias", "Dias", 60),
            ("saldo", "Saldo", 70),
            ("precio", "Precio", 90),
            ("descuento", "Descuento", 90),
            ("sugerido", "Precio sugerido", 120),
        ):
            self._tabla.heading(clave, text=titulo)
            self._tabla.column(clave, width=ancho, anchor="w")
        self._tabla.tag_configure("vencido", foreground="#a11")
        self._tabla.pack(fill="both", expand=True, pady=4)
        self._tabla_lotes = None
        if self._repo_lotes is not None:
            ttk.Label(self, text="Lotes", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
            self._tabla_lotes = ttk.Treeview(
                self, columns=("lote", "producto", "vence", "saldo"), show="headings", height=6
            )
            for clave, titulo, ancho in (
                ("lote", "Lote", 80),
                ("producto", "Producto", 260),
                ("vence", "Vence", 110),
                ("saldo", "Saldo", 80),
            ):
                self._tabla_lotes.heading(clave, text=titulo)
                self._tabla_lotes.column(clave, width=ancho, anchor="w")
            self._tabla_lotes.pack(fill="x", pady=4)
        ttk.Label(
            self,
            text="El descuento es una sugerencia (politica propuesta); no modifica el precio.",
            foreground="#666",
        ).pack(anchor="w")
        self.refrescar()

    # ------------------------------------------- Registrar merma o ajuste (HU-INV-04) --

    def _construir_merma(self) -> None:
        marco = ttk.LabelFrame(self, text="Registrar merma o ajuste", padding=10)
        marco.pack(fill="x", pady=(8, 0))
        self._merma_codigo = tk.StringVar()
        self._merma_cantidad = tk.StringVar()
        self._merma_motivo = tk.StringVar()
        self._merma_obs = tk.StringVar()
        self._merma_estado = tk.StringVar(value="Existencia actual: -  ·  Resultante: -")
        campos = (
            ("Codigo de producto", ttk.Entry(marco, textvariable=self._merma_codigo, width=18)),
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
                    width=18,
                ),
            ),
            ("Observacion", ttk.Entry(marco, textvariable=self._merma_obs, width=26)),
        )
        for columna, (titulo, widget) in enumerate(campos):
            ttk.Label(marco, text=titulo).grid(row=0, column=columna, sticky="w", padx=4)
            widget.grid(row=1, column=columna, padx=4, pady=(2, 0), sticky="w")
        for variable in (self._merma_codigo, self._merma_cantidad):
            variable.trace_add("write", lambda *_a: self._actualizar_estado_merma())
        ttk.Button(marco, text="Registrar merma", command=self._registrar_merma).grid(
            row=1, column=len(campos), padx=8
        )
        ttk.Label(marco, textvariable=self._merma_estado, foreground="#666").grid(
            row=2, column=0, columnspan=len(campos), sticky="w", padx=4, pady=(6, 0)
        )
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
        self.refrescar()

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
        self._cantidad.set("")
        self._codigo_lote.set("")
        self._vence.set("")
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
        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True)
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
        self._pestanas.add(self._panel_entrada, text="Entrada y alertas")
        self._paneles: list = []
        if consultar_existencias is not None and definir_minimo is not None:
            self.existencias = PanelExistencias(
                self._pestanas, consultar_existencias, definir_minimo, repo_categorias
            )
            self._pestanas.add(self.existencias, text="Existencias")
            self._paneles.append(self.existencias)
        if reporte_inventario is not None:
            self.reporte = PanelReporteInventario(
                self._pestanas, reporte_inventario, repo_categorias
            )
            self._pestanas.add(self.reporte, text="Reporte de inventario")
            self._paneles.append(self.reporte)
        if consultar_movimientos is not None:
            self.movimientos = PanelMovimientos(self._pestanas, consultar_movimientos)
            self._pestanas.add(self.movimientos, text="Movimientos")
            self._paneles.append(self.movimientos)

    def __getattr__(self, nombre: str):
        """La pestana de entrada conserva sus nombres de siempre (_codigo, _registrar, ...)."""
        if nombre.startswith("__") or nombre == "_panel_entrada":
            raise AttributeError(nombre)
        return getattr(self._panel_entrada, nombre)

    def refrescar(self) -> None:
        self._panel_entrada.refrescar()
        for panel in self._paneles:
            panel.refrescar()

    def al_mostrar(self) -> None:
        self.refrescar()
