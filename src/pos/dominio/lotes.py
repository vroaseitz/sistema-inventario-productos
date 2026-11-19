"""Lotes con fecha de vencimiento y descuento sugerido (HU-INV-02, HU-INV-03, HU-INV-06).

Un producto perecible puede tener varios lotes (misma mercaderia, distinto vencimiento).
Al vender se consume primero el lote que vence antes (FEFO). La alerta de vencimiento
sugiere un descuento sobre el lote segun cuanto le queda de vida.

La politica de descuento (dos etapas, editable por producto) la definio la Product Owner el
17-11-2026 (ver docs/08-diseno/adr/0005-politica-descuento-vencimiento.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import uuid4

from .errores import DatosProductoInvalidos, ReglaInventarioInvalida
from .value_objects import Dinero


@dataclass
class Lote:
    codigo_producto: str
    fecha_vencimiento: date
    saldo: Decimal
    id: int | None = None
    # Identificador estable para sincronizar con Supabase sin depender del id local.
    uuid: str = field(default_factory=lambda: str(uuid4()))
    # I-02: codigo de lote impreso en el envase (p. ej. «L. 26089 A»); vacio si no se escribio.
    codigo_lote: str = ""

    def __post_init__(self) -> None:
        self.saldo = Decimal(str(self.saldo))
        if self.saldo < 0:
            raise ReglaInventarioInvalida("El saldo de un lote no puede ser negativo")

    @property
    def etiqueta(self) -> str:
        """Lo que se muestra al usuario: el codigo impreso o, si no hay, «L» + numero interno."""
        return self.codigo_lote or f"L{self.id}"

    def dias_para_vencer(self, hoy: date) -> int:
        """Dias que le quedan al lote (negativo si ya vencio)."""
        return (self.fecha_vencimiento - hoy).days

    def esta_vencido(self, hoy: date) -> bool:
        return self.dias_para_vencer(hoy) < 0


def proponer_lote(lotes: list[Lote], preferido_uuid: str | None = None) -> Lote | None:
    """Lote del que saldra el producto: el elegido a mano o, si no, el que vence antes (FEFO)."""
    con_saldo = sorted((x for x in lotes if x.saldo > 0), key=lambda x: x.fecha_vencimiento)
    if preferido_uuid is not None:
        for lote in con_saldo:
            if lote.uuid == preferido_uuid:
                return lote
    return con_saldo[0] if con_saldo else None


def consumir_fefo(
    lotes: list[Lote], cantidad: Decimal, preferido_uuid: str | None = None
) -> Decimal:
    """Descuenta `cantidad` de los lotes, primero el que vence antes (FEFO).

    Si la cajera eligio otro lote (`preferido_uuid`, F5 Cambiar lote) se consume ese primero.

    Modifica los saldos en su lugar y devuelve lo que NO pudo cubrir con lotes (stock sin
    lote asociado, p. ej. mercaderia ingresada antes de que existieran los lotes).
    """
    pendiente = Decimal(str(cantidad))
    if pendiente <= 0:
        raise ReglaInventarioInvalida("La cantidad a consumir debe ser mayor que cero")
    orden = sorted(lotes, key=lambda x: (x.uuid != preferido_uuid, x.fecha_vencimiento))
    for lote in orden:
        if pendiente == 0:
            break
        tomado = min(lote.saldo, pendiente)
        lote.saldo -= tomado
        pendiente -= tomado
    return pendiente


@dataclass(frozen=True)
class PoliticaDescuento:
    """Descuento sugerido por vencimiento, en dos etapas (O-42, definido por la PO el 17-11).

    Por defecto: 20 % desde 14 dias antes de vencer y 50 % desde 7 dias antes (etapa final). Los
    dias y los porcentajes se pueden editar por producto (el pan dura 2 semanas; otros productos,
    meses). Un lote ya vencido no se rebaja: no se debe vender.
    """

    dias_inicial: int = 14
    pct_inicial: int = 20
    dias_final: int = 7
    pct_final: int = 50

    def __post_init__(self) -> None:
        for dias in (self.dias_inicial, self.dias_final):
            if dias < 1:
                raise DatosProductoInvalidos("Los días de cada etapa deben ser 1 o más")
        for pct in (self.pct_inicial, self.pct_final):
            if not 1 <= pct <= 100:
                raise DatosProductoInvalidos("El porcentaje de descuento debe estar entre 1 y 100")
        if self.dias_final >= self.dias_inicial:
            raise DatosProductoInvalidos(
                "La etapa final del descuento debe empezar más cerca del vencimiento"
            )

    def porcentaje(self, dias_restantes: int) -> int:
        if dias_restantes < 0:
            return 0
        if dias_restantes <= self.dias_final:
            return self.pct_final
        if dias_restantes <= self.dias_inicial:
            return self.pct_inicial
        return 0

    def con_ajustes(
        self,
        dias_1: int | None = None,
        pct_1: int | None = None,
        dias_2: int | None = None,
        pct_2: int | None = None,
    ) -> PoliticaDescuento:
        """La politica con los valores propios de un producto; lo que va vacio usa esta."""
        return PoliticaDescuento(
            dias_1 if dias_1 is not None else self.dias_inicial,
            pct_1 if pct_1 is not None else self.pct_inicial,
            dias_2 if dias_2 is not None else self.dias_final,
            pct_2 if pct_2 is not None else self.pct_final,
        )


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
