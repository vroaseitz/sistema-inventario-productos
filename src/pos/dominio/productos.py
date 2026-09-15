"""Entidad Producto y sus reglas."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from .errores import DatosProductoInvalidos
from .value_objects import Costo, Dinero


class UnidadVenta(Enum):
    """Como se vende el producto."""

    UNIDAD = "unidad"  # se vende por pieza (1, 2, 3...)
    GRANEL = "granel"  # se vende por peso (kg)


@dataclass
class Producto:
    """Producto del catalogo.

    `codigo` es el codigo interno de la tienda (el que llevan embebido las etiquetas
    de balanza para productos a granel). Un producto a granel se identifica por
    `unidad_venta == GRANEL` y su precio se interpreta como precio por kilo.
    """

    codigo: str
    nombre: str
    precio: Dinero
    unidad_venta: UnidadVenta = UnidadVenta.UNIDAD
    categoria_id: int | None = None
    activo: bool = True
    costo: Costo | None = None
    _validado: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not self.codigo or not self.codigo.strip():
            raise DatosProductoInvalidos("El producto requiere un codigo")
        if not self.nombre or not self.nombre.strip():
            raise DatosProductoInvalidos("El producto requiere un nombre")
        if not isinstance(self.precio, Dinero):
            raise DatosProductoInvalidos("El precio debe ser un value object Dinero")

    @property
    def es_granel(self) -> bool:
        return self.unidad_venta is UnidadVenta.GRANEL

    @property
    def margen(self) -> Decimal | None:
        """Margen sobre venta: (precio - costo neto) / precio.

        `None` si el producto no tiene costo capturado todavia.
        """
        if self.costo is None:
            return None
        if self.precio.monto == 0:
            raise DatosProductoInvalidos("No se puede calcular margen con precio 0")
        diferencia = self.precio.monto - self.costo.neto.monto
        return (Decimal(diferencia) / Decimal(self.precio.monto)).quantize(Decimal("0.0001"))

    @property
    def markup(self) -> Decimal | None:
        """Markup sobre costo: (precio - costo neto) / costo neto.

        `None` si el producto no tiene costo capturado todavia (HU-PRD-08:
        costo `None`), o si el costo neto cargado es legitimamente cero (el
        markup sobre cero no esta definido, pero a diferencia del caso
        anterior esto no es un dato faltante).
        """
        if self.costo is None or self.costo.neto.monto == 0:
            return None
        diferencia = self.precio.monto - self.costo.neto.monto
        return (Decimal(diferencia) / Decimal(self.costo.neto.monto)).quantize(Decimal("0.0001"))

    def calcular_total(self, cantidad) -> Dinero:
        """Total para una cantidad dada.

        - UNIDAD: cantidad es entero (numero de piezas).
        - GRANEL: cantidad es Decimal de kilos; precio es por kilo.
        """
        from decimal import Decimal

        if self.es_granel:
            return self.precio.multiplicado_por(Decimal(str(cantidad)))
        if int(cantidad) != cantidad or cantidad < 0:
            raise DatosProductoInvalidos("Un producto por unidad requiere cantidad entera >= 0")
        return self.precio.multiplicado_por(Decimal(int(cantidad)))
