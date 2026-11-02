"""Categorias de producto (C-02, HU-PRD-10).

Las categorias viven en una tabla, no en el codigo. `CATEGORIAS_VALIDADAS` son las 20 que
valido la Product Owner con Roxana (CA-02): son la semilla de una base nueva y se agregan a
las bases existentes. Las 4 de la primera version (`CATEGORIAS_ANTIGUAS`) se eliminan.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errores import DatosProductoInvalidos

# Orden de la lista de la PO: es el orden en que se muestran en la pantalla F2.
CATEGORIAS_VALIDADAS = (
    "Frutos secos y semillas",
    "Harinas y legumbres",
    "Granolas y cereales",
    "Superalimentos",
    "Snacks y barras",
    "Chocolates y dulces",
    "Líquidos",
    "Leches vegetales",
    "Lácteos y huevos",
    "Quesos y alternativas veganas",
    "Congelados",
    "Helados",
    "Panadería y repostería",
    "Frutas y verduras",
    "Aceites, untables y endulzantes",
    "Café, té y yerba mate",
    "Pastas y productos sin gluten",
    "Vitaminas y suplementos",
    "Cosmética natural",
    "Plantas",
)
CATEGORIAS_INICIALES = CATEGORIAS_VALIDADAS

CATEGORIAS_ANTIGUAS = ("frutas", "verduras", "abarrotes", "limpieza")
# Unicas con equivalente claro en la lista validada. 'abarrotes' y 'limpieza' no lo tienen:
# si algun producto las usa hay que reasignarlo a mano (editar el producto en F2).
REASIGNACION_ANTIGUAS = {"frutas": "Frutas y verduras", "verduras": "Frutas y verduras"}


@dataclass(frozen=True)
class Categoria:
    id: int
    nombre: str


def normalizar_nombre_categoria(nombre: str) -> str:
    """Quita espacios sobrantes y exige un nombre no vacio."""
    limpio = " ".join(nombre.split())
    if not limpio:
        raise DatosProductoInvalidos("La categoria requiere un nombre")
    return limpio
