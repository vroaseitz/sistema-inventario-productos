"""Repositorio de existencias y ajustes de inventario sobre SQLite."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from pos.aplicacion.puertos import RepositorioAjustes, RepositorioExistencias
from pos.dominio.inventario import AjusteInventario, Existencia, MotivoAjuste


class RepositorioExistenciasSQLite(RepositorioExistencias):
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def obtener(self, codigo_producto: str) -> Existencia | None:
        fila = self._con.execute(
            "SELECT * FROM existencias WHERE codigo_producto = ?", (codigo_producto,)
        ).fetchone()
        if not fila:
            return None
        return Existencia(fila["codigo_producto"], Decimal(fila["cantidad"]))

    def guardar(self, existencia: Existencia) -> None:
        self._con.execute(
            """
            INSERT INTO existencias (codigo_producto, cantidad)
            VALUES (?, ?)
            ON CONFLICT(codigo_producto) DO UPDATE SET cantidad=excluded.cantidad
            """,
            (existencia.codigo_producto, str(existencia.cantidad)),
        )


class RepositorioAjustesSQLite(RepositorioAjustes):
    """Implementación de RepositorioAjustes para SQLite (HU Registro de mermas y ajustes)."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar_ajuste(self, ajuste: AjusteInventario) -> None:
        motivo_valor = ajuste.motivo.value if isinstance(ajuste.motivo, MotivoAjuste) else str(ajuste.motivo)
        fecha_str = ajuste.fecha.isoformat() if hasattr(ajuste.fecha, "isoformat") else str(ajuste.fecha)

        self._con.execute(
            """
            INSERT INTO historial_ajustes_inventario (
                codigo_producto,
                cantidad_anterior,
                cantidad_nueva,
                diferencia_conteo,
                motivo,
                usuario,
                fecha
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ajuste.codigo_producto,
                str(ajuste.cantidad_anterior),
                str(ajuste.cantidad_nueva),
                str(ajuste.diferencia_conteo),
                motivo_valor,
                ajuste.usuario,
                fecha_str,
            ),
        )

