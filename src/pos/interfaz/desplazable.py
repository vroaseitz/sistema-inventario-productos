"""Marco con barra de desplazamiento vertical para pantallas más altas que la ventana.

La ventana se ajusta al área útil de la pantalla (ver `tamano_de_ventana`), y en un portátil o con
la pantalla escalada al 150 % la pestaña «Caja y corte» no cabe entera. Con este marco, lo que no
cabe se alcanza con la rueda del mouse o la barra, en vez de quedar recortado sin aviso.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class MarcoDesplazable(ttk.Frame):
    """Contenedor: se agregan los widgets a `.interior`, que crece a lo alto que necesite."""

    def __init__(self, padre: tk.Misc) -> None:
        super().__init__(padre)
        self._lienzo = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self._barra = ttk.Scrollbar(self, orient="vertical", command=self._lienzo.yview)
        self._lienzo.configure(yscrollcommand=self._barra.set)
        self._barra.pack(side="right", fill="y")
        self._lienzo.pack(side="left", fill="both", expand=True)
        self.interior = ttk.Frame(self._lienzo)
        self._ventana = self._lienzo.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", self._ajustar_region)
        self._lienzo.bind("<Configure>", self._ajustar_ancho)
        # La rueda solo actúa mientras el puntero está sobre el marco (no en otras pestañas).
        self.bind("<Enter>", self._activar_rueda)
        self.bind("<Leave>", self._desactivar_rueda)

    def _ajustar_region(self, _evento: object = None) -> None:
        self._lienzo.configure(scrollregion=self._lienzo.bbox("all"))

    def _ajustar_ancho(self, evento: tk.Event) -> None:
        # El contenido ocupa todo el ancho disponible (sus tablas se estiran con la ventana).
        self._lienzo.itemconfigure(self._ventana, width=evento.width)

    def _activar_rueda(self, _evento: object = None) -> None:
        self.bind_all("<MouseWheel>", self._rueda)

    def _desactivar_rueda(self, evento: tk.Event) -> None:
        # <Leave> también salta al entrar a un hijo: solo se suelta si el puntero salió del marco.
        x, y = self.winfo_pointerxy()
        if self.winfo_containing(x, y) is None or not str(self.winfo_containing(x, y)).startswith(
            str(self)
        ):
            self.unbind_all("<MouseWheel>")

    def _rueda(self, evento: tk.Event) -> None:
        if self.interior.winfo_reqheight() <= self._lienzo.winfo_height():
            return
        self._lienzo.yview_scroll(int(-evento.delta / 120), "units")
