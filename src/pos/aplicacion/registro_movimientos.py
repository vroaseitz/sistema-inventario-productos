"""Deja cada entrada, venta, merma o ajuste en el historial de inventario (HU-INV-08).

Como el `Auditor`, toma el usuario de una funcion: la sesion puede cambiar sin reconstruir nada.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from pos.aplicacion.puertos import RepositorioMovimientos
from pos.dominio.inventario import MovimientoInventario, TipoMovimiento


@dataclass
class RegistroMovimientos:
    repositorio: RepositorioMovimientos
    usuario: Callable[[], str]

    def registrar(
        self, codigo: str, tipo: TipoMovimiento, cantidad: Decimal | int, motivo: str = ""
    ) -> None:
        self.repositorio.registrar(
            MovimientoInventario(codigo, tipo, Decimal(str(cantidad)), motivo, self.usuario())
        )
