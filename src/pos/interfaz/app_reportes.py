"""Pantalla F6 Reportes: ventas por periodo y categoria (HU-REP-02)."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.reporte_ventas import SIN_CATEGORIA, ReporteVentas


def _clp(monto: int) -> str:
    return "$" + f"{monto:,}".replace(",", ".")


class VentanaReportes(ttk.Frame):
    def __init__(self, parent: tk.Misc, reporte_ventas: ReporteVentas) -> None:
        super().__init__(parent, padding=12)
        self._reporte = reporte_ventas
        hoy = date.today().isoformat()
        self._desde = tk.StringVar(value=hoy)
        self._hasta = tk.StringVar(value=hoy)
        self._resumen = tk.StringVar()

        filtros = ttk.LabelFrame(self, text="Ventas por periodo y categoria", padding=10)
        filtros.pack(fill="x")
        for columna, (texto, variable) in enumerate(
            (("Desde (AAAA-MM-DD)", self._desde), ("Hasta (AAAA-MM-DD)", self._hasta))
        ):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            ttk.Entry(filtros, textvariable=variable, width=20).grid(row=1, column=columna, padx=4)
        ttk.Button(filtros, text="Generar", command=self.generar).grid(row=1, column=2, padx=8)
        ttk.Label(self, textvariable=self._resumen, font=("TkDefaultFont", 11, "bold")).pack(
            anchor="w", pady=8
        )

        self._por_categoria = self._tabla("Por categoria", ("Categoria", "Vendido"))
        self._por_medio = self._tabla("Por medio de pago", ("Medio", "Cobrado"))
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
                    ("Sin categoria" if c == SIN_CATEGORIA else f"Categoria {c}", _clp(m))
                    for c, m in sorted(datos.por_categoria.items())
                ],
            ),
            (self._por_medio, [(k, _clp(m)) for k, m in sorted(datos.por_medio_pago.items())]),
        ):
            tabla.delete(*tabla.get_children())
            for fila in filas:
                tabla.insert("", "end", values=fila)
