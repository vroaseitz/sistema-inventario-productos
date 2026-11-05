"""Exportar una tabla a CSV (el boton «Exportar» de los reportes del prototipo).

El archivo usa punto y coma y BOM UTF-8: asi Excel en espanol lo abre con las tildes y las
columnas bien separadas.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from pathlib import Path
from tkinter import filedialog, messagebox


def escribir_csv(ruta: str | Path, encabezados: Sequence[str], filas: Iterable[Sequence]) -> int:
    """Escribe el CSV y devuelve cuantas filas de datos quedaron."""
    cantidad = 0
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(encabezados)
        for fila in filas:
            escritor.writerow(fila)
            cantidad += 1
    return cantidad


def exportar_con_dialogo(
    nombre_sugerido: str, encabezados: Sequence[str], filas: list[Sequence]
) -> None:
    ruta = filedialog.asksaveasfilename(
        title="Exportar",
        defaultextension=".csv",
        initialfile=nombre_sugerido,
        filetypes=[("CSV (Excel)", "*.csv")],
    )
    if not ruta:
        return  # canceló
    try:
        cantidad = escribir_csv(ruta, encabezados, filas)
    except OSError as error:
        messagebox.showerror("Exportar", f"No se pudo guardar el archivo: {error}")
        return
    messagebox.showinfo("Exportar", f"Se exportaron {cantidad} filas a\n{ruta}")
