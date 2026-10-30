"""Caso de uso: agregar a inventario un producto, con lote y vencimiento (HU-INV-01/02).

Cierra el hallazgo C-12: lo creado en Catalogo no se podia vender porque no habia como
ingresar su stock. Un producto perecible EXIGE fecha de vencimiento; uno no perecible la
acepta de forma opcional.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pos.aplicacion.casos_uso.ajustar_stock import AjustarStock
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioExistencias,
    RepositorioLotes,
    RepositorioProductos,
)
from pos.aplicacion.sincronizacion import encolar_lote
from pos.dominio.errores import DatosProductoInvalidos, ReglaInventarioInvalida
from pos.dominio.lotes import Lote


@dataclass
class IngresarStock:
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias
    repositorio_lotes: RepositorioLotes
    cola: ColaSincronizacion | None = None

    def ejecutar(
        self,
        codigo_producto: str,
        cantidad: Decimal | float,
        motivo: str,
        fecha_vencimiento: date | None = None,
        hoy: date | None = None,
    ) -> Lote | None:
        producto = self.repositorio_productos.obtener_por_codigo(codigo_producto)
        if producto is None:
            raise DatosProductoInvalidos(f"No existe un producto con codigo {codigo_producto}")
        if producto.perecible and fecha_vencimiento is None:
            raise ReglaInventarioInvalida(
                "Un producto perecible requiere fecha de vencimiento para ingresar stock"
            )
        if fecha_vencimiento is not None and fecha_vencimiento < (hoy or date.today()):
            raise ReglaInventarioInvalida("No se puede ingresar un lote ya vencido")

        cantidad_dec = Decimal(str(cantidad))
        # AjustarStock valida el motivo obligatorio y la cantidad > 0, y encola el stock.
        AjustarStock(self.repositorio_existencias, cola=self.cola).ingresar(
            codigo_producto, cantidad_dec, motivo
        )
        if fecha_vencimiento is None:
            return None
        lote = Lote(codigo_producto, fecha_vencimiento, cantidad_dec)
        self.repositorio_lotes.guardar(lote)
        encolar_lote(self.cola, lote)
        return lote
