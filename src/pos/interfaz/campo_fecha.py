"""Campo de fecha con calendario desplegable (R-01).

Se puede seguir escribiendo la fecha (AAAA-MM-DD) o hacer clic en el campo / en el boton para
elegir el dia en un calendario pequeno. Expone `get()` y `set()` como un StringVar para poder
reemplazarlo sin tocar el resto de la pantalla.
"""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

MESES = (
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
)
DIAS = ("L", "M", "M", "J", "V", "S", "D")


def _interpretar(texto: str) -> date | None:
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


class CampoFecha(ttk.Frame):
    def __init__(self, parent: tk.Misc, valor: date | None = None, width: int = 14) -> None:
        super().__init__(parent)
        self._texto = tk.StringVar(value=valor.isoformat() if valor else "")
        self._entrada = ttk.Entry(self, textvariable=self._texto, width=width)
        self._entrada.pack(side="left")
        ttk.Button(self, text="▾", width=2, command=self.alternar).pack(side="left", padx=(2, 0))
        self._entrada.bind("<Button-1>", lambda _e: self.after(1, self.abrir), add="+")
        self._popup: tk.Toplevel | None = None
        self._mes = (valor or date.today()).replace(day=1)

    # -- API como la de un StringVar ------------------------------------------------------
    def get(self) -> str:
        return self._texto.get()

    def set(self, valor: str | date) -> None:
        self._texto.set(valor.isoformat() if isinstance(valor, date) else valor)

    # -- calendario -------------------------------------------------------------------------
    @property
    def abierto(self) -> bool:
        return self._popup is not None

    def alternar(self) -> None:
        self.cerrar() if self.abierto else self.abrir()

    def abrir(self) -> None:
        if self.abierto:
            return
        actual = _interpretar(self._texto.get())
        self._mes = (actual or date.today()).replace(day=1)
        popup = tk.Toplevel(self)
        popup.transient(self.winfo_toplevel())
        popup.resizable(False, False)
        popup.title("Elegir fecha")
        popup.bind("<Escape>", lambda _e: self.cerrar())
        popup.protocol("WM_DELETE_WINDOW", self.cerrar)
        x = self._entrada.winfo_rootx()
        y = self._entrada.winfo_rooty() + self._entrada.winfo_height() + 2
        popup.geometry(f"+{x}+{y}")
        self._popup = popup
        self._dibujar()
        popup.focus_set()

    def cerrar(self) -> None:
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None

    def _mover(self, meses: int) -> None:
        indice = self._mes.year * 12 + (self._mes.month - 1) + meses
        self._mes = date(indice // 12, indice % 12 + 1, 1)
        self._dibujar()

    def _elegir(self, dia: date) -> None:
        self.set(dia)
        self.cerrar()

    def _dibujar(self) -> None:
        popup = self._popup
        if popup is None:
            return
        for hijo in popup.winfo_children():
            hijo.destroy()
        marco = ttk.Frame(popup, padding=6)
        marco.pack()
        ttk.Button(marco, text="‹", width=2, command=lambda: self._mover(-1)).grid(row=0, column=0)
        ttk.Label(marco, text=f"{MESES[self._mes.month - 1]} {self._mes.year}").grid(
            row=0, column=1, columnspan=5
        )
        ttk.Button(marco, text="›", width=2, command=lambda: self._mover(1)).grid(row=0, column=6)
        for columna, nombre in enumerate(DIAS):
            ttk.Label(marco, text=nombre).grid(row=1, column=columna)
        elegido = _interpretar(self._texto.get())
        hoy = date.today()
        semanas = calendar.Calendar(firstweekday=0).monthdayscalendar(
            self._mes.year, self._mes.month
        )
        for fila, semana in enumerate(semanas, start=2):
            for columna, numero in enumerate(semana):
                if numero == 0:
                    continue
                dia = date(self._mes.year, self._mes.month, numero)
                marca = "•" if dia == elegido else ("·" if dia == hoy else "")
                ttk.Button(
                    marco,
                    text=f"{numero}{marca}",
                    width=3,
                    command=lambda d=dia: self._elegir(d),
                ).grid(row=fila, column=columna)
