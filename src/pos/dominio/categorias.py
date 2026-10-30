"""Catalogo de categorias de productos.

Reemplaza la tupla fijada en codigo (`CATEGORIAS_VALIDAS`) por un catalogo
dinamico persistido en la tabla `categoria` (misma estructura que la migracion
PostgreSQL de `database/migraciones/002_modelo_completo.sql`). La lista valida
la define el negocio en la BD, no el codigo: agregar una categoria no exige
un deploy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Categoria:
    """Una categoria del catalogo (ej. 'frutas', 'panaderia')."""

    id: int
    nombre: str

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("El id de categoria debe ser positivo")
        if not self.nombre or not self.nombre.strip():
            raise ValueError("La categoria requiere un nombre")
