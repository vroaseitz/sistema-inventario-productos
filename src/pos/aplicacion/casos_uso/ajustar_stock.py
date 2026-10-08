"""Caso de uso: ajustar el stock de un producto (ingreso, descuento y registro de ajustes/mermas)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pos.aplicacion.puertos import RepositorioAjustes, RepositorioExistencias
from pos.dominio.errores import ReglaInventarioInvalida
from pos.dominio.inventario import AjusteInventario, Existencia, MotivoAjuste


@dataclass
class AjustarStock:
    repositorio_existencias: RepositorioExistencias
    repositorio_ajustes: RepositorioAjustes | None = None

    def __init__(
        self,
        repositorio_existencias: RepositorioExistencias,
        repositorio_ajustes: RepositorioAjustes | None = None,
    ) -> None:
        self.repositorio_existencias = repositorio_existencias
        self.repositorio_ajustes = repositorio_ajustes

    @property
    def repositorio(self) -> RepositorioExistencias:
        """Alias para mantener compatibilidad con código existente."""
        return self.repositorio_existencias

    def ejecutar(
        self,
        codigo_producto: str,
        cantidad_real_contada: float | Decimal,
        motivo: MotivoAjuste,
        usuario: str,
    ) -> AjusteInventario:
        """Registra un ajuste de inventario (físico, merma, robo, etc.) y actualiza el stock."""
        cantidad_contada_dec = Decimal(str(cantidad_real_contada))
        if cantidad_contada_dec < 0:
            raise ReglaInventarioInvalida("La cantidad contada no puede ser negativa")

        existencia = self.repositorio_existencias.obtener(codigo_producto)
        if existencia is None:
            existencia = Existencia(codigo_producto=codigo_producto, cantidad=Decimal("0"))

        cantidad_anterior = existencia.cantidad

        ajuste = AjusteInventario(
            codigo_producto=codigo_producto,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=cantidad_contada_dec,
            motivo=motivo,
            usuario=usuario,
        )

        existencia.cantidad = cantidad_contada_dec

        self.repositorio_existencias.guardar(existencia)
        if self.repositorio_ajustes is not None:
            self.repositorio_ajustes.guardar_ajuste(ajuste)

        return ajuste

    def ingresar(self, codigo_producto: str, cantidad: Decimal | float) -> Existencia:
        existencia = self.repositorio_existencias.obtener(codigo_producto) or Existencia(codigo_producto)
        existencia.ingresar(Decimal(str(cantidad)))
        self.repositorio_existencias.guardar(existencia)
        return existencia

    def descontar(self, codigo_producto: str, cantidad: Decimal | float) -> Existencia:
        existencia = self.repositorio_existencias.obtener(codigo_producto)
        if existencia is None:
            raise ReglaInventarioInvalida(f"No hay existencia registrada para {codigo_producto}")
        existencia.descontar(Decimal(str(cantidad)))
        self.repositorio_existencias.guardar(existencia)
        return existencia
