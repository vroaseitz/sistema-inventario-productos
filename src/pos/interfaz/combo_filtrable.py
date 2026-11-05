"""Lista desplegable en la que se puede escribir para filtrar (CA-18).

Se escribe parte del nombre y la lista se acorta (sin distinguir tildes ni mayusculas; primero los
que empiezan con lo escrito). Enter o salir del campo eligen el primero que quede. Lo escrito que
no corresponde a ninguna opcion no se acepta: el campo vuelve al ultimo valor valido, asi nunca
llega a la pantalla un nombre de categoria que no existe.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
import unicodedata
from collections.abc import Iterable
from tkinter import ttk

_TECLAS_DE_NAVEGACION = {
    "Up",
    "Down",
    "Left",
    "Right",
    "Return",
    "KP_Enter",
    "Tab",
    "ISO_Left_Tab",
    "Escape",
    "Shift_L",
    "Shift_R",
    "Control_L",
    "Control_R",
    "Alt_L",
    "Alt_R",
    "Home",
    "End",
}


def sin_tildes(texto: str) -> str:
    """Minusculas y sin tildes: «Té» y «te» son lo mismo al buscar."""
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def filtrar_opciones(opciones: Iterable[str], escrito: str) -> list[str]:
    """Las opciones que contienen lo escrito; primero las que empiezan con ello."""
    clave = sin_tildes(escrito.strip())
    if not clave:
        return list(opciones)
    empiezan, contienen = [], []
    for opcion in opciones:
        plano = sin_tildes(opcion)
        if plano.startswith(clave):
            empiezan.append(opcion)
        elif clave in plano:
            contienen.append(opcion)
    return empiezan + contienen


class ComboFiltrable(ttk.Combobox):
    def __init__(
        self,
        parent: tk.Misc,
        variable: tk.StringVar,
        valores: Iterable[str],
        width: int = 24,
    ) -> None:
        self._todas = list(valores)
        super().__init__(parent, textvariable=variable, values=self._todas, width=width)
        self._variable = variable
        self._ultimo_valido = variable.get()
        self.bind("<KeyRelease>", self._al_escribir, add="+")
        self.bind("<<ComboboxSelected>>", self._al_elegir, add="+")
        self.bind("<Return>", lambda _e: self.confirmar(), add="+")
        self.bind("<FocusOut>", self._al_salir, add="+")

    def poner_opciones(self, valores: Iterable[str]) -> None:
        """Reemplaza las opciones (p. ej. al crear una categoria nueva)."""
        self._todas = list(valores)
        self.configure(values=self._todas)

    def _al_elegir(self, _evento: object = None) -> None:
        self._ultimo_valido = self._variable.get()
        self.configure(values=self._todas)

    def _al_escribir(self, evento: tk.Event) -> None:
        if evento.keysym in _TECLAS_DE_NAVEGACION:
            return
        self.configure(values=filtrar_opciones(self._todas, self._variable.get()))

    def _al_salir(self, _evento: object = None) -> None:
        # Abrir la lista desplegable tambien quita el foco al campo: ahi no se confirma.
        self.after(1, self._confirmar_si_salio)

    def _confirmar_si_salio(self) -> None:
        try:
            foco = self.focus_get()
        except KeyError:  # el foco esta en el popup de la lista (no es un widget con nombre)
            return
        if foco is not None and "popdown" in str(foco):
            return
        with contextlib.suppress(tk.TclError):  # la ventana ya se cerro
            self.confirmar()

    def confirmar(self) -> None:
        """Deja un valor valido: la opcion exacta, la primera que coincide, o el ultimo valido."""
        texto = self._variable.get()
        if texto in self._todas:
            nuevo = texto
        else:
            coincidencias = filtrar_opciones(self._todas, texto) if texto.strip() else []
            nuevo = coincidencias[0] if coincidencias else self._ultimo_valido
        self.configure(values=self._todas)
        cambio = nuevo != self._ultimo_valido
        self._variable.set(nuevo)
        self._ultimo_valido = nuevo
        if cambio:
            # Quien escucha la eleccion (p. ej. refrescar la lista) la ve igual que con el mouse.
            self.event_generate("<<ComboboxSelected>>")
