"""Repositorio de productos sobre SQLite. Implementa el puerto RepositorioProductos."""

from __future__ import annotations

import sqlite3

from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Dinero


class RepositorioProductosSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, producto: Producto) -> None:
        # SQL parametrizado (nunca interpolacion de strings): evita inyeccion SQL.
        self._con.execute(
            """
            INSERT INTO productos (codigo, nombre, precio, unidad_venta, categoria, activo)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                nombre=excluded.nombre,
                precio=excluded.precio,
                unidad_venta=excluded.unidad_venta,
                categoria=excluded.categoria,
                activo=excluded.activo
            """,
            (
                producto.codigo,
                producto.nombre,
                producto.precio.monto,
                producto.unidad_venta.value,
                producto.categoria,
                1 if producto.activo else 0,
            ),
        )

    def obtener_por_codigo(self, codigo: str) -> Producto | None:
        fila = self._con.execute("SELECT * FROM productos WHERE codigo = ?", (codigo,)).fetchone()
        return self._a_producto(fila) if fila else None

    def listar(self) -> list[Producto]:
        filas = self._con.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
        return [self._a_producto(f) for f in filas]

    @staticmethod
    def _a_producto(fila: sqlite3.Row) -> Producto:
        return Producto(
            codigo=fila["codigo"],
            nombre=fila["nombre"],
            precio=Dinero(int(fila["precio"])),
            unidad_venta=UnidadVenta(fila["unidad_venta"]),
            categoria=fila["categoria"],
            activo=bool(fila["activo"]),
        )
