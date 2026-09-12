"""Caso de uso: ajustar el stock de un producto (ingreso o descuento)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pos.aplicacion.puertos import RepositorioExistencias
from pos.dominio.errores import ReglaInventarioInvalida
from pos.dominio.inventario import Existencia


@dataclass
class AjustarStock:
    repositorio: RepositorioExistencias

    def ingresar(self, codigo_producto: str, cantidad: Decimal) -> Existencia:
        existencia = self.repositorio.obtener(codigo_producto) or Existencia(codigo_producto)
        existencia.ingresar(Decimal(str(cantidad)))
        self.repositorio.guardar(existencia)
        return existencia

    def descontar(self, codigo_producto: str, cantidad: Decimal) -> Existencia:
        existencia = self.repositorio.obtener(codigo_producto)
        if existencia is None:
            raise ReglaInventarioInvalida(f"No hay existencia registrada para {codigo_producto}")
        existencia.descontar(Decimal(str(cantidad)))
        self.repositorio.guardar(existencia)
        return existencia
