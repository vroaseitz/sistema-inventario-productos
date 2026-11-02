"""Pantalla F6 Reportes: ventas por periodo y categoria (HU-REP-02)."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.reporte_ventas import SIN_CATEGORIA, ReporteVentas
from pos.aplicacion.puertos import RepositorioCategorias
from pos.dominio.pagos import MedioPago
from pos.interfaz.campo_fecha import CampoFecha


def _clp(monto: int) -> str:
    return "$" + f"{monto:,}".replace(",", ".")


_NOMBRES_MEDIO = {
    MedioPago.EFECTIVO.value: "Efectivo",
    MedioPago.TARJETA.value: "Tarjeta",
    MedioPago.TRANSFERENCIA.value: "Transferencia",
    MedioPago.CREDITO_CLIENTE.value: "Crédito cliente",
}


def _nombre_medio(valor: str) -> str:
    return _NOMBRES_MEDIO.get(valor, valor.replace("_", " ").capitalize())


class VentanaReportes(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        reporte_ventas: ReporteVentas,
        repo_categorias: RepositorioCategorias | None = None,
    ) -> None:
        super().__init__(parent, padding=12)
        self._reporte = reporte_ventas
        self._categorias = repo_categorias
        self._hoy_al_generar = date.today()
        # R-01: fechas con calendario desplegable (tambien se puede escribir AAAA-MM-DD).
        self._desde: CampoFecha
        self._hasta: CampoFecha
        self._resumen = tk.StringVar()

        filtros = ttk.LabelFrame(self, text="Ventas por periodo y categoria", padding=10)
        filtros.pack(fill="x")
        self._desde = CampoFecha(filtros, date.today(), width=14)
        self._hasta = CampoFecha(filtros, date.today(), width=14)
        for columna, (texto, campo) in enumerate((("Desde", self._desde), ("Hasta", self._hasta))):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            campo.grid(row=1, column=columna, padx=4, sticky="w")
        ttk.Button(filtros, text="Generar", command=self.generar).grid(row=1, column=2, padx=8)
        ttk.Label(self, textvariable=self._resumen, font=("TkDefaultFont", 11, "bold")).pack(
            anchor="w", pady=8
        )

        self._por_categoria = self._tabla("Por categoria", ("Categoria", "Vendido"))
        self._por_medio = self._tabla("Por medio de pago", ("Medio", "Cobrado"))
        self.generar()

    def _nombre_categoria(self, categoria_id: int) -> str:
        if categoria_id == SIN_CATEGORIA:
            return "Sin categoría"
        nombre = self._categorias.nombre_de(categoria_id) if self._categorias else None
        return nombre or "Sin categoría"

    def al_mostrar(self) -> None:
        """R-02: el reporte se armaba solo al abrir la app y quedaba vacio; ahora se regenera.

        Si el dia cambio desde la ultima vez y las fechas seguian en «hoy», se actualizan.
        """
        hoy = date.today()
        if hoy != self._hoy_al_generar:
            for campo in (self._desde, self._hasta):
                if campo.get().strip() == self._hoy_al_generar.isoformat():
                    campo.set(hoy.isoformat())
            self._hoy_al_generar = hoy
        self.generar()

    def _tabla(self, titulo: str, columnas: tuple[str, str]) -> ttk.Treeview:
        ttk.Label(self, text=titulo).pack(anchor="w")
        tabla = ttk.Treeview(self, columns=columnas, show="headings", height=6)
        for columna in columnas:
            tabla.heading(columna, text=columna)
        tabla.pack(fill="x", pady=(0, 8))
        return tabla

    def generar(self) -> None:
        try:
            desde = datetime.strptime(self._desde.get().strip(), "%Y-%m-%d").date()
            hasta = datetime.strptime(self._hasta.get().strip(), "%Y-%m-%d").date()
            datos = self._reporte.ejecutar(desde, hasta)
        except ValueError as error:
            messagebox.showerror("Reportes", f"Revisa las fechas: {error}")
            return
        self._resumen.set(
            f"{datos.cantidad_ventas} ventas · total {_clp(datos.total)} · "
            f"ticket promedio {_clp(datos.ticket_promedio)}"
        )
        for tabla, filas in (
            (
                self._por_categoria,
                [
                    (self._nombre_categoria(c), _clp(m))
                    for c, m in sorted(
                        datos.por_categoria.items(), key=lambda x: self._nombre_categoria(x[0])
                    )
                ],
            ),
            (
                self._por_medio,
                [(_nombre_medio(k), _clp(m)) for k, m in sorted(datos.por_medio_pago.items())],
            ),
        ):
            tabla.delete(*tabla.get_children())
            for fila in filas:
                tabla.insert("", "end", values=fila)
