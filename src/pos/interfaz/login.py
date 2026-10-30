"""Dialogo de acceso (HU-USR-01). En el primer uso crea el administrador."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from pos.dominio.errores import ErrorDominio
from pos.dominio.usuarios import Usuario


class DialogoAcceso(tk.Toplevel):
    """Modal. `resultado` queda con el Usuario autenticado, o None si se cancelo."""

    def __init__(
        self,
        parent: tk.Misc,
        accion: Callable[[str, str], Usuario],
        primer_uso: bool,
    ) -> None:
        super().__init__(parent)
        self.resultado: Usuario | None = None
        self._accion = accion
        self.title("NaturalSur - Crear administrador" if primer_uso else "NaturalSur - Ingresar")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        marco = ttk.Frame(self, padding=18)
        marco.pack()
        if primer_uso:
            ttk.Label(
                marco,
                text="Primer uso: crea el usuario administrador\n(clave de al menos 8 caracteres).",
            ).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        self.nombre = tk.StringVar()
        self.clave = tk.StringVar()
        self.error = tk.StringVar()
        ttk.Label(marco, text="Usuario").grid(row=1, column=0, sticky="w")
        entrada = ttk.Entry(marco, textvariable=self.nombre, width=26)
        entrada.grid(row=1, column=1, pady=3)
        ttk.Label(marco, text="Clave").grid(row=2, column=0, sticky="w")
        clave = ttk.Entry(marco, textvariable=self.clave, show="*", width=26)
        clave.grid(row=2, column=1, pady=3)
        ttk.Label(marco, textvariable=self.error, foreground="#a11").grid(
            row=3, column=0, columnspan=2
        )
        ttk.Button(marco, text="Entrar", command=self.confirmar).grid(
            row=4, column=0, columnspan=2, pady=(8, 0)
        )
        self.bind("<Return>", lambda _e: self.confirmar())
        entrada.focus_set()

    def confirmar(self) -> None:
        try:
            self.resultado = self._accion(self.nombre.get(), self.clave.get())
        except ErrorDominio as error:
            self.error.set(str(error))
            self.clave.set("")
            return
        self.destroy()


def pedir_acceso(
    parent: tk.Misc, accion: Callable[[str, str], Usuario], primer_uso: bool
) -> Usuario | None:
    dialogo = DialogoAcceso(parent, accion, primer_uso)
    # A-03: en Windows un dialogo transient de una ventana oculta (withdraw) tampoco se ve.
    # Solo se asocia a la ventana principal si esta visible; si no, va al frente por su cuenta.
    if parent.winfo_viewable():
        dialogo.transient(parent)  # type: ignore[arg-type]
    dialogo.deiconify()
    dialogo.lift()
    dialogo.attributes("-topmost", True)
    dialogo.after(300, lambda: dialogo.attributes("-topmost", False))
    dialogo.focus_force()
    dialogo.grab_set()
    parent.wait_window(dialogo)
    return dialogo.resultado
