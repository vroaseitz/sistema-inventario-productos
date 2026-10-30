"""Pantalla F3 Inventario: entrada de stock con vencimiento y alertas con descuento sugerido.

Cubre HU-INV-01/02 (ingreso con lote) y HU-INV-03/06 (alerta de vencimiento con descuento
sugerido). La politica de descuento es una propuesta pendiente de validar con la PO.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.puertos import RepositorioLotes, RepositorioProductos
from pos.dominio.errores import ErrorDominio
from pos.interfaz.campo_fecha import CampoFecha


def _clp(monto: int) -> str:
    return "$" + f"{monto:,}".replace(",", ".")


class VentanaInventario(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        repo_productos: RepositorioProductos,
        ingresar_stock: IngresarStock,
        consultar_alertas: ConsultarAlertasVencimiento,
        repo_lotes: RepositorioLotes | None = None,
    ) -> None:
        super().__init__(parent, padding=12)
        self._productos = repo_productos
        self._ingresar = ingresar_stock
        self._alertas = consultar_alertas
        self._repo_lotes = repo_lotes

        self._codigo = tk.StringVar()
        self._cantidad = tk.StringVar()
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
            ("Motivo", self._motivo),
        )
        for columna, (etiqueta, variable) in enumerate(campos):
            ttk.Label(formulario, text=etiqueta).grid(row=0, column=columna, sticky="w", padx=4)
            if variable is self._vence:
                self._vence.grid(row=1, column=columna, padx=4, pady=(2, 0), sticky="w")
                continue
            ttk.Entry(formulario, textvariable=variable, width=22).grid(
                row=1, column=columna, padx=4, pady=(2, 0)
            )
        ttk.Button(formulario, text="Ingresar", command=self._registrar).grid(
            row=1, column=len(campos), padx=8
        )
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

    def _registrar(self) -> None:
        try:
            vence = self._vence.get().strip()
            fecha = datetime.strptime(vence, "%Y-%m-%d").date() if vence else None
            self._ingresar.ejecutar(
                self._codigo.get().strip(),
                self._cantidad.get().strip().replace(",", "."),
                self._motivo.get(),
                fecha_vencimiento=fecha,
            )
        except ValueError:
            messagebox.showerror("Inventario", "Revisa cantidad y fecha (AAAA-MM-DD).")
            return
        except ErrorDominio as error:
            messagebox.showerror("Inventario", str(error))
            return
        self._mensaje.set(f"Stock ingresado: {self._codigo.get().strip()}")
        self._cantidad.set("")
        self._vence.set("")
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
                    f"L{lote.id}",
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
