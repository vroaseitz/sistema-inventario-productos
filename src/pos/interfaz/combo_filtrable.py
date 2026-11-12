"""Lista desplegable en la que se puede escribir para filtrar (CA-18).

Se escribe parte del nombre y la lista se despliega y se acorta con cada letra (sin distinguir
tildes ni mayusculas; primero los que empiezan con lo escrito), sin quitar el foco al campo. Las
flechas recorren la lista; Enter o salir del campo eligen la resaltada (o la primera). Lo escrito
que no corresponde a ninguna opcion no se acepta: el campo vuelve al ultimo valor valido, asi
nunca llega a la pantalla un nombre de categoria que no existe.
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
        self._popup: tk.Toplevel | None = None  # lista emergente que se acorta al escribir
        self._lista: tk.Listbox | None = None
        self._clic_en_popup = False
        self.bind("<KeyRelease>", self._al_escribir, add="+")
        self.bind("<<ComboboxSelected>>", self._al_elegir, add="+")
        self.bind("<Return>", self._al_enter, add="+")
        self.bind("<KP_Enter>", self._al_enter, add="+")
        self.bind("<Down>", lambda _e: self._mover(1))
        self.bind("<Up>", lambda _e: self._mover(-1))
        self.bind("<Escape>", lambda _e: self._cerrar_popup(), add="+")
        self.bind("<FocusOut>", self._al_salir, add="+")
        self.bind("<Destroy>", lambda _e: self._cerrar_popup(), add="+")

    def poner_opciones(self, valores: Iterable[str]) -> None:
        """Reemplaza las opciones (p. ej. al crear una categoria nueva)."""
        self._todas = list(valores)
        self.configure(values=self._todas)

    def fijar(self, valor: str) -> None:
        """Pone un valor desde el programa (sin disparar la eleccion) y lo da por valido."""
        self._cerrar_popup()
        self._variable.set(valor)
        self._ultimo_valido = valor

    def _al_elegir(self, _evento: object = None) -> None:
        self._ultimo_valido = self._variable.get()
        self.configure(values=self._todas)
        self._cerrar_popup()

    def _al_escribir(self, evento: tk.Event) -> None:
        if evento.keysym in _TECLAS_DE_NAVEGACION:
            return
        escrito = self._variable.get()
        coinciden = filtrar_opciones(self._todas, escrito)
        self.configure(values=coinciden)
        if escrito.strip() and coinciden:
            self._mostrar_popup(coinciden)
        else:
            self._cerrar_popup()

    # --- lista emergente: no toma el foco, asi se puede seguir escribiendo ---

    def _mostrar_popup(self, opciones: list[str]) -> None:
        if self._popup is None:
            self._popup = tk.Toplevel(self)
            self._popup.overrideredirect(True)
            self._popup.attributes("-topmost", True)
            self._lista = tk.Listbox(self._popup, activestyle="none", exportselection=False)
            self._lista.pack(fill="both", expand=True)
            self._lista.bind("<ButtonPress-1>", lambda _e: setattr(self, "_clic_en_popup", True))
            self._lista.bind("<ButtonRelease-1>", self._elegir_de_popup)
        lista = self._lista
        assert lista is not None
        lista.delete(0, "end")
        for opcion in opciones:
            lista.insert("end", opcion)
        lista.configure(height=min(len(opciones), 8))
        lista.selection_set(0)
        self._popup.update_idletasks()
        x, y = self.winfo_rootx(), self.winfo_rooty() + self.winfo_height()
        self._popup.geometry(f"{self.winfo_width()}x{lista.winfo_reqheight()}+{x}+{y}")
        self._popup.lift()

    def _cerrar_popup(self) -> None:
        if self._popup is not None:
            with contextlib.suppress(tk.TclError):
                self._popup.destroy()
        self._popup = None
        self._lista = None

    def _resaltada(self) -> str | None:
        if self._lista is None:
            return None
        seleccion = self._lista.curselection()
        return self._lista.get(seleccion[0]) if seleccion else None

    def _mover(self, delta: int) -> str | None:
        """Flechas: recorren la lista emergente (sin ella, queda el comportamiento normal)."""
        lista = self._lista
        if self._popup is None or lista is None or not lista.size():
            return None
        seleccion = lista.curselection()
        nuevo = max(0, min((seleccion[0] if seleccion else -1) + delta, lista.size() - 1))
        lista.selection_clear(0, "end")
        lista.selection_set(nuevo)
        lista.see(nuevo)
        return "break"

    def _elegir_de_popup(self, _evento: object = None) -> None:
        self._clic_en_popup = False
        elegida = self._resaltada()
        if elegida is not None:
            self._variable.set(elegida)
            self.confirmar()
        self.focus_set()

    def _al_enter(self, _evento: object = None) -> None:
        elegida = self._resaltada()
        if elegida is not None:  # Enter elige lo resaltado (por defecto, la primera que queda)
            self._variable.set(elegida)
        self.confirmar()

    def _al_salir(self, _evento: object = None) -> None:
        # Abrir la lista desplegable tambien quita el foco al campo: ahi no se confirma.
        self.after(1, self._confirmar_si_salio)

    def _confirmar_si_salio(self) -> None:
        if self._clic_en_popup:  # el clic en la lista emergente quita el foco, pero aun no eligio
            return
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
        self._cerrar_popup()
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
