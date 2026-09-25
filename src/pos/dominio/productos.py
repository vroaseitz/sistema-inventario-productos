"""Entidad Producto y sus reglas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .errores import DatosProductoInvalidos
from .value_objects import Dinero

from datetime import datetime


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
    categoria_id: str  # Ahora es obligatorio y representa una referencia
    unidad_venta: UnidadVenta = UnidadVenta.UNIDAD
    es_perecible: bool = False
    dias_aviso_vencimiento: int | None = None
    activo: bool = True
    _validado: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not self.codigo or not self.codigo.strip():
            raise DatosProductoInvalidos("El producto requiere un codigo")
        
        if not self.nombre or not self.nombre.strip():
            raise DatosProductoInvalidos("El producto requiere un nombre")
        # Normalización del nombre
        self.nombre = self.nombre.strip().upper()

        if not isinstance(self.precio, Dinero):
            raise DatosProductoInvalidos("El precio debe ser un value object Dinero")
            
        # Validación estricta de categoría
        if not self.categoria_id or not str(self.categoria_id).strip():
            raise DatosProductoInvalidos("El sistema impide guardar un producto sin categoria asignada")
            
        # Validación de producto perecible
        if self.es_perecible and (self.dias_aviso_vencimiento is None or self.dias_aviso_vencimiento < 0):
            raise DatosProductoInvalidos("Un producto perecible requiere indicar con cuantos dias avisar antes del vencimiento")

    @property
    def es_granel(self) -> bool:
        return self.unidad_venta is UnidadVenta.GRANEL

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
@dataclass
class RegistroCambioPrecio:
    """Registro inmutable de un cambio de precio (HU-PRD-05)."""
    codigo_producto: str
    precio_anterior: Dinero
    precio_nuevo: Dinero
    usuario: str
    fecha: datetime = field(default_factory=datetime.now)
    
    