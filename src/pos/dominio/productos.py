"""Entidad Producto y sus reglas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .errores import DatosProductoInvalidos
from .lotes import PoliticaDescuento
from .value_objects import Costo, Dinero, _a_pesos, neto_de_precio


class UnidadVenta(Enum):
    """Como se vende el producto."""

    UNIDAD = "unidad"  # se vende por pieza (1, 2, 3...)
    GRANEL = "granel"  # se vende por peso (kg)


CATEGORIAS_VALIDAS = ("frutas", "verduras", "abarrotes", "limpieza")

# CA-21 / HU-PRD-02: impuesto adicional a bebidas (IABA): 10 % (bajo en azucar) o 18 % (azucaradas).
TASAS_IABA = (10, 18)


def costo_con_iaba(neto: int, iaba_pct: int | None) -> Costo:
    """Costo neto con su IABA calculado aparte (el IVA se captura en la factura, no aqui)."""
    adicional = _a_pesos(Decimal(neto) * iaba_pct / 100) if iaba_pct else 0
    return Costo(neto=Dinero(neto), iva=Dinero(0), impuesto_adicional=Dinero(adicional))


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
    perecible: bool = False
    dias_aviso: int | None = None
    stock_minimo: int | None = None  # HU-INV-05: bajo este numero de unidades se avisa
    # O-42: etapas del descuento por vencimiento propias del producto; None = politica por defecto.
    desc_dias_1: int | None = None
    desc_pct_1: int | None = None
    desc_dias_2: int | None = None
    desc_pct_2: int | None = None
    # CA-21: tasa del impuesto adicional a bebidas (10 o 18); None = no esta afecto.
    iaba_pct: int | None = None
    _validado: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not self.codigo or not self.codigo.strip():
            raise DatosProductoInvalidos("El producto requiere un código")
        if not self.nombre or not self.nombre.strip():
            raise DatosProductoInvalidos("El producto requiere un nombre")
        if not isinstance(self.precio, Dinero):
            raise DatosProductoInvalidos("El precio debe ser un value object Dinero")
        if self.categoria_id is None:
            raise DatosProductoInvalidos("El producto requiere una categoría (C-04)")
        if self.stock_minimo is not None and self.stock_minimo < 0:
            raise DatosProductoInvalidos("El stock mínimo no puede ser negativo")
        if self.perecible and (self.dias_aviso is None or self.dias_aviso <= 0):
            raise DatosProductoInvalidos("Un producto perecible requiere dias_aviso (C-05a)")
        if self.iaba_pct is not None and self.iaba_pct not in TASAS_IABA:
            raise DatosProductoInvalidos("El impuesto adicional a bebidas es de 10 % o 18 %")
        self.politica_descuento()  # valida los ajustes propios de descuento (O-42)

    def fijar_costo_neto(self, neto: int) -> None:
        """Guarda el costo neto del producto con su IABA calculado segun su tasa (CA-21)."""
        self.costo = costo_con_iaba(neto, self.iaba_pct)

    def politica_descuento(self, base: PoliticaDescuento | None = None) -> PoliticaDescuento:
        """Descuento por vencimiento de este producto: sus etapas propias o las por defecto."""
        return (base or PoliticaDescuento()).con_ajustes(
            self.desc_dias_1, self.desc_pct_1, self.desc_dias_2, self.desc_pct_2
        )

    @property
    def es_granel(self) -> bool:
        return self.unidad_venta is UnidadVenta.GRANEL

    @property
    def margen(self) -> Decimal | None:
        """Margen sobre venta neta: (precio neto - costo neto) / precio neto (ADR 0004).

        El precio de venta incluye IVA; se lleva a neto antes de compararlo con el costo.
        `None` si el producto no tiene costo capturado todavia.
        """
        if self.costo is None:
            return None
        if self.precio.monto == 0:
            raise DatosProductoInvalidos("No se puede calcular margen con precio 0")
        precio_neto = neto_de_precio(self.precio.monto)
        diferencia = precio_neto - self.costo.para_margen.monto
        return (Decimal(diferencia) / Decimal(precio_neto)).quantize(Decimal("0.0001"))

    @property
    def markup(self) -> Decimal | None:
        """Markup sobre costo: (precio neto - costo neto) / costo neto.

        `None` si el producto no tiene costo capturado todavia (HU-PRD-08:
        costo `None`), o si el costo neto cargado es legitimamente cero (el
        markup sobre cero no esta definido, pero a diferencia del caso
        anterior esto no es un dato faltante).
        """
        if self.costo is None or self.costo.para_margen.monto == 0:
            return None
        base = self.costo.para_margen.monto
        diferencia = neto_de_precio(self.precio.monto) - base
        return (Decimal(diferencia) / Decimal(base)).quantize(Decimal("0.0001"))

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
    motivo: str = ""
