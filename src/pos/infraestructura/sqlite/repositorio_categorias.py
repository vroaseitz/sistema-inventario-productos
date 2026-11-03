"""Repositorio de categorias sobre SQLite. Implementa RepositorioCategorias."""

from __future__ import annotations

import sqlite3
import unicodedata

from pos.dominio.categorias import (
    CATEGORIAS_ANTIGUAS,
    REASIGNACION_ANTIGUAS,
    Categoria,
    normalizar_nombre_categoria,
)


def _clave(nombre: str) -> str:
    """Compara sin tildes ni mayusculas: 'Lácteos' y 'lacteos' son la misma categoria."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c)
    )
    return sin_tildes.lower()


class RepositorioCategoriasSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def listar(self) -> list[Categoria]:
        filas = self._con.execute("SELECT id, nombre FROM categorias ORDER BY id").fetchall()
        return [Categoria(f["id"], f["nombre"]) for f in filas]

    def nombre_de(self, categoria_id: int | None) -> str | None:
        if categoria_id is None:
            return None
        fila = self._con.execute(
            "SELECT nombre FROM categorias WHERE id = ?", (categoria_id,)
        ).fetchone()
        return fila["nombre"] if fila else None

    def agregar(self, nombre: str) -> tuple[Categoria, bool]:
        """Agrega la categoria si no existe (sin distinguir tildes/mayusculas).

        Devuelve (categoria, creada). Nunca renombra ni cambia el id de una existente: los
        productos ya guardados apuntan a ese id.
        """
        nombre = normalizar_nombre_categoria(nombre)
        for existente in self.listar():
            if _clave(existente.nombre) == _clave(nombre):
                return existente, False
        cursor = self._con.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        return Categoria(cursor.lastrowid, nombre), True

    def sembrar(self, nombres: list[str] | tuple[str, ...]) -> int:
        """Agrega las que falten y devuelve cuantas creo."""
        return sum(1 for nombre in nombres if self.agregar(nombre)[1])

    def depurar_antiguas(self, reasignar: dict[str, str] | None = None) -> list[str]:
        """Elimina las 4 categorias de la primera version (CA-02) y devuelve las que quito.

        `reasignar` (nombre antiguo -> nombre nuevo) mueve antes sus productos a otra categoria
        que ya exista. Una categoria antigua que todavia tiene productos y no tiene destino se
        deja como esta: no se pierde la categoria de un producto.
        """
        destinos = {_clave(k): v for k, v in (reasignar or REASIGNACION_ANTIGUAS).items()}
        eliminadas = []
        for categoria in self.listar():
            clave = _clave(categoria.nombre)
            if clave not in CATEGORIAS_ANTIGUAS:
                continue
            if clave in destinos:
                nuevo = next(
                    (c for c in self.listar() if _clave(c.nombre) == _clave(destinos[clave])), None
                )
                if nuevo is not None:
                    self._con.execute(
                        "UPDATE productos SET categoria_id = ? WHERE categoria_id = ?",
                        (nuevo.id, categoria.id),
                    )
            en_uso = self._con.execute(
                "SELECT 1 FROM productos WHERE categoria_id = ? LIMIT 1", (categoria.id,)
            ).fetchone()
            if en_uso is None:
                self._con.execute("DELETE FROM categorias WHERE id = ?", (categoria.id,))
                eliminadas.append(categoria.nombre)
        return eliminadas
