"""Cuadro de formulario simple y modal. Enter acepta y Esc cancela.

`campos` es una lista de (clave, titulo, valor_inicial, opciones) donde opciones puede ser:
"clave" (texto oculto), una lista de valores (lista desplegable) o None (texto normal). La funcion
`aceptar` recibe un dict {clave: texto} y devuelve True si todo salio bien (el cuadro se cierra) o
False si mostro un error (el cuadro queda abierto para corregir).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

Campo = tuple[str, str, str, "str | list[str] | None"]


def pedir_formulario(
    parent: tk.Misc,
    titulo: str,
    campos: list[Campo],
    aceptar: Callable[[dict[str, str]], bool],
    texto_boton: str = "Guardar",
    nota: str = "",
) -> tk.Toplevel:
    ventana = tk.Toplevel(parent)
    ventana.title(titulo)
    ventana.transient(parent.winfo_toplevel())
    fila = 0
    if nota:
        ttk.Label(ventana, text=nota, foreground="#666", wraplength=360).grid(
            row=fila, column=0, columnspan=2, padx=12, pady=(10, 4)
        )
        fila += 1
    variables: dict[str, tk.StringVar] = {}
    primera = True
    for clave, etiqueta, inicial, opciones in campos:
        ttk.Label(ventana, text=etiqueta).grid(row=fila, column=0, sticky="w", padx=12, pady=4)
        variables[clave] = tk.StringVar(value=inicial)
        if isinstance(opciones, list):
            widget = ttk.Combobox(
                ventana, textvariable=variables[clave], values=opciones, state="readonly", width=24
            )
        else:
            widget = ttk.Entry(
                ventana,
                textvariable=variables[clave],
                width=26,
                show="*" if opciones == "clave" else "",
            )
        widget.grid(row=fila, column=1, padx=12, pady=4)
        if primera:
            widget.focus_set()
            primera = False
        fila += 1

    def confirmar(_evento: object = None) -> None:
        if aceptar({clave: variable.get() for clave, variable in variables.items()}):
            ventana.destroy()

    ventana.bind("<Return>", confirmar)  # Enter acepta, Esc cancela
    ventana.bind("<Escape>", lambda _e: ventana.destroy())
    botones = ttk.Frame(ventana)
    botones.grid(row=fila, column=0, columnspan=2, pady=10)
    ttk.Button(botones, text=texto_boton, command=confirmar).pack(side="left", padx=6)
    ttk.Button(botones, text="Cancelar", command=ventana.destroy).pack(side="left", padx=6)
    ventana.grab_set()
    ventana.confirmar = confirmar  # type: ignore[attr-defined]
    ventana.variables = variables  # type: ignore[attr-defined]
    return ventana
