"""Categorias de producto (C-02, HU-PRD-10).

Las categorias viven en una tabla, no en el codigo. `CATEGORIAS_INICIALES` es solo la semilla
de una base nueva; la lista validada por la Product Owner se carga con
`scripts/cargar_categorias.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errores import DatosProductoInvalidos
from .productos import CATEGORIAS_VALIDAS

CATEGORIAS_INICIALES = CATEGORIAS_VALIDAS


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
