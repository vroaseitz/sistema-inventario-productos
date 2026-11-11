"""Avisos compartidos entre pantallas.

CO-08: el costo no debe superar al precio sin avisar. El sistema antiguo tenia 9 productos con
el costo mayor que el precio. Se compara igual que el margen (ADR 0004): el costo neto contra
el precio SIN IVA, asi «Almendras» a $3.990 con costo $5.000 da ganancia -$1.647.
"""

from __future__ import annotations

from tkinter import messagebox

from pos.dominio.formato import formatear_clp
from pos.dominio.value_objects import neto_de_precio

MENSAJE_MARGEN_NEGATIVO = "El costo supera el precio de venta (margen negativo)"


def margen_negativo(costo_neto: int | None, precio: int | None) -> bool:
    """True si el costo neto supera al precio sin IVA (se venderia con perdida)."""
    if not costo_neto or not precio:
        return False
    return costo_neto > neto_de_precio(precio)


def costo_bajo_el_precio_o_confirmado(nombre: str, costo_neto: int | None, precio: int) -> bool:
    """CO-08: si el costo deja margen negativo, pregunta antes de seguir. True = seguir."""
    if not margen_negativo(costo_neto, precio):
        return True
    precio_neto = neto_de_precio(precio)
    ganancia = precio_neto - (costo_neto or 0)
    return messagebox.askyesno(
        "Margen negativo",
        f"{MENSAJE_MARGEN_NEGATIVO}.\n\n"
        f"{nombre}: precio {formatear_clp(precio)} (sin IVA {formatear_clp(precio_neto)})"
        f", costo neto {formatear_clp(costo_neto or 0)}.\n"
        f"Ganancia por unidad: {formatear_clp(ganancia)}.\n\n¿Guardar igual?",
    )
