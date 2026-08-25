"""Caso de uso: escanear un codigo de barras en caja.

Analiza el codigo (normal o interno con peso embebido), busca el producto y calcula
el total de la linea de venta. No toca inventario ni persistencia: es orquestacion
de lectura, por lo que es facil de testear.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pos.aplicacion.puertos import RepositorioProductos
from pos.dominio.codigo_barras import (
    TipoValorEmbebido,
    analizar_codigo,
)
from pos.dominio.errores import CodigoBarrasInvalido
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero


@dataclass
class LineaVenta:
    producto: Producto
    cantidad: Decimal
    total: Dinero


@dataclass
class EscanearCodigo:
    repositorio: RepositorioProductos
    tipo_valor: TipoValorEmbebido = TipoValorEmbebido.PESO_GRAMOS

    def ejecutar(self, codigo: str) -> LineaVenta:
        lectura = analizar_codigo(codigo, tipo_valor=self.tipo_valor)
        producto = self.repositorio.obtener_por_codigo(lectura.codigo_producto)
        if producto is None:
            raise CodigoBarrasInvalido(f"No hay producto para el codigo {lectura.codigo_producto}")
        if lectura.es_granel and lectura.peso_kg is not None:
            cantidad = lectura.peso_kg
        elif lectura.es_granel and lectura.precio is not None:
            # El codigo trae precio embebido: la cantidad efectiva es 1 "porcion".
            return LineaVenta(
                producto=producto, cantidad=Decimal("1"), total=Dinero(int(lectura.precio))
            )
        else:
            cantidad = Decimal("1")
        return LineaVenta(
            producto=producto, cantidad=cantidad, total=producto.calcular_total(cantidad)
        )
