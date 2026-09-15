"""Caso de uso: ajustar el stock de un producto (ingreso o descuento)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pos.aplicacion.puertos import RepositorioExistencias
from pos.dominio.errores import ReglaInventarioInvalida
from pos.dominio.inventario import Existencia


@dataclass
class AjustarStock:
    """Ajuste manual de stock (HU-INV-04): el motivo es obligatorio.

    Corrige el defecto del sistema legado, donde 29.715 ajustes manuales de
    inventario quedaron sin ninguna causa registrada, haciendo imposible
    distinguir una correccion de digitacion de una merma real.
    """

    repositorio: RepositorioExistencias

    def ingresar(self, codigo_producto: str, cantidad: Decimal, motivo: str) -> Existencia:
        self._validar_motivo(motivo)
        existencia = self.repositorio.obtener(codigo_producto) or Existencia(codigo_producto)
        existencia.ingresar(Decimal(str(cantidad)))
        self.repositorio.guardar(existencia)
        return existencia

    def descontar(self, codigo_producto: str, cantidad: Decimal, motivo: str) -> Existencia:
        self._validar_motivo(motivo)
        existencia = self.repositorio.obtener(codigo_producto)
        if existencia is None:
            raise ReglaInventarioInvalida(f"No hay existencia registrada para {codigo_producto}")
        existencia.descontar(Decimal(str(cantidad)))
        self.repositorio.guardar(existencia)
        return existencia

    @staticmethod
    def _validar_motivo(motivo: str) -> None:
        if not motivo or not motivo.strip():
            raise ReglaInventarioInvalida("El ajuste de stock requiere un motivo")
