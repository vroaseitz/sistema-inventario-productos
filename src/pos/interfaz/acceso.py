"""Cuadro para que cada persona cambie su propia contrasena (HU-USR-01)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from pos.aplicacion.casos_uso.gestionar_usuarios import GestionarUsuarios
from pos.dominio.errores import ErrorDominio
from pos.interfaz.dialogo_formulario import pedir_formulario


def cambiar_clave_de(gestion: GestionarUsuarios, nombre: str, valores: dict[str, str]) -> bool:
    """Cambia la clave con lo escrito en el cuadro; muestra el motivo si no se pudo."""
    try:
        gestion.cambiar_mi_clave(nombre, valores["actual"], valores["nueva"], valores["repetir"])
    except ErrorDominio as error:
        messagebox.showerror("Mi contraseña", str(error))
        return False
    messagebox.showinfo("Mi contraseña", "Tu contraseña se cambió")
    return True


def dialogo_cambiar_clave(parent: tk.Misc, nombre: str, gestion: GestionarUsuarios) -> tk.Toplevel:
    return pedir_formulario(
        parent,
        "Mi contraseña",
        [
            ("actual", "Contraseña actual", "", "clave"),
            ("nueva", "Contraseña nueva (mínimo 8)", "", "clave"),
            ("repetir", "Repetir la nueva", "", "clave"),
        ],
        lambda valores: cambiar_clave_de(gestion, nombre, valores),
        "Cambiar contraseña",
    )
