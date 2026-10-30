"""Caso de uso: reporte de ventas por periodo y categoria (HU-REP-02).

Solo cuenta ventas pagadas. El total por categoria suma los subtotales de las lineas; el
total por medio de pago suma lo cobrado (en efectivo, el monto ya redondeado a la decena).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from pos.aplicacion.puertos import RepositorioProductos, RepositorioVentas

SIN_CATEGORIA = 0


@dataclass(frozen=True)
class ReporteVentasPeriodo:
    desde: date
    hasta: date
    cantidad_ventas: int
    total: int
    por_categoria: dict[int, int] = field(default_factory=dict)
    por_medio_pago: dict[str, int] = field(default_factory=dict)

    @property
    def ticket_promedio(self) -> int:
        return round(self.total / self.cantidad_ventas) if self.cantidad_ventas else 0


@dataclass
class ReporteVentas:
    repositorio_ventas: RepositorioVentas
    repositorio_productos: RepositorioProductos

    def ejecutar(self, desde: date, hasta: date) -> ReporteVentasPeriodo:
        if hasta < desde:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        ventas = self.repositorio_ventas.por_periodo(desde, hasta)
        categorias: dict[str, int] = {}
        por_categoria: dict[int, int] = {}
        por_medio: dict[str, int] = {}
        total = 0
        for venta in ventas:
            total += venta.total_pagado.monto
            for pago in venta.pagos:
                por_medio[pago.medio.value] = por_medio.get(pago.medio.value, 0) + pago.monto.monto
            for detalle in venta.detalles:
                codigo = detalle.producto_codigo
                if codigo not in categorias:
                    producto = self.repositorio_productos.obtener_por_codigo(codigo)
                    categorias[codigo] = (
                        producto.categoria_id if producto is not None else SIN_CATEGORIA
                    )
                categoria = categorias[codigo]
                por_categoria[categoria] = por_categoria.get(categoria, 0) + detalle.subtotal.monto
        return ReporteVentasPeriodo(desde, hasta, len(ventas), total, por_categoria, por_medio)
