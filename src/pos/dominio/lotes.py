"""Lotes con fecha de vencimiento y descuento sugerido (HU-INV-02, HU-INV-03, HU-INV-06).

Un producto perecible puede tener varios lotes (misma mercaderia, distinto vencimiento).
Al vender se consume primero el lote que vence antes (FEFO). La alerta de vencimiento
sugiere un descuento sobre el lote segun cuanto le queda de vida.

La politica de descuento por defecto es una PROPUESTA del equipo de desarrollo, aun sin
validar con la Product Owner (ver docs/08-diseno/adr/0005-politica-descuento-vencimiento.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import uuid4

from .errores import ReglaInventarioInvalida
from .value_objects import Dinero


@dataclass
class Lote:
    codigo_producto: str
    fecha_vencimiento: date
    saldo: Decimal
    id: int | None = None
    # Identificador estable para sincronizar con Supabase sin depender del id local.
    uuid: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        self.saldo = Decimal(str(self.saldo))
        if self.saldo < 0:
            raise ReglaInventarioInvalida("El saldo de un lote no puede ser negativo")

    def dias_para_vencer(self, hoy: date) -> int:
        """Dias que le quedan al lote (negativo si ya vencio)."""
        return (self.fecha_vencimiento - hoy).days

    def esta_vencido(self, hoy: date) -> bool:
        return self.dias_para_vencer(hoy) < 0


def consumir_fefo(lotes: list[Lote], cantidad: Decimal) -> Decimal:
    """Descuenta `cantidad` de los lotes, primero el que vence antes (FEFO).

    Modifica los saldos en su lugar y devuelve lo que NO pudo cubrir con lotes (stock sin
    lote asociado, p. ej. mercaderia ingresada antes de que existieran los lotes).
    """
    pendiente = Decimal(str(cantidad))
    if pendiente <= 0:
        raise ReglaInventarioInvalida("La cantidad a consumir debe ser mayor que cero")
    for lote in sorted(lotes, key=lambda x: x.fecha_vencimiento):
        if pendiente == 0:
            break
        tomado = min(lote.saldo, pendiente)
        lote.saldo -= tomado
        pendiente -= tomado
    return pendiente


@dataclass(frozen=True)
class PoliticaDescuento:
    """Descuento sugerido segun los dias que le quedan al lote.

    `tramos` es una tupla (dias_maximos, porcentaje) de menor a mayor; el primer tramo cuyo
    `dias_maximos` alcance a los dias restantes define el descuento. Si el lote esta dentro
    del aviso del producto pero fuera de todos los tramos, se aplica `porcentaje_aviso`.
    Un lote ya vencido no se rebaja: no se debe vender.
    """

    tramos: tuple[tuple[int, int], ...] = ((3, 30), (7, 20))
    porcentaje_aviso: int = 10

    def porcentaje(self, dias_restantes: int, dias_aviso: int | None) -> int:
        if dias_restantes < 0:
            return 0
        for dias_maximos, porcentaje in self.tramos:
            if dias_restantes <= dias_maximos:
                return porcentaje
        if dias_aviso is not None and dias_restantes <= dias_aviso:
            return self.porcentaje_aviso
        return 0


@dataclass(frozen=True)
class AlertaVencimiento:
    lote: Lote
    nombre_producto: str
    precio_actual: Dinero
    dias_restantes: int
    descuento_pct: int

    @property
    def vencido(self) -> bool:
        return self.dias_restantes < 0

    @property
    def precio_sugerido(self) -> Dinero:
        """Precio con el descuento sugerido (igual al actual si no corresponde rebaja)."""
        factor = Decimal(100 - self.descuento_pct) / Decimal(100)
        return self.precio_actual.multiplicado_por(factor)
