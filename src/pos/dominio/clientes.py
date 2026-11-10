"""Clientes con credito y su cuenta (HU-CLI-01 a HU-CLI-05, HU-CAJ-03).

El credito es solo para familiares, segun lo definido por las propietarias. El saldo NO se guarda
en ninguna parte: se calcula sumando los movimientos (consumos suman, abonos restan). Un
movimiento registrado no se edita: un error se corrige con otro movimiento que queda a la vista.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from .errores import ReglaClienteInvalida
from .formato import formatear_clp
from .value_objects import _a_pesos

MEDIOS_ABONO = ("efectivo", "transferencia", "tarjeta")
# El descuento del credito familiar se asienta como un abono sin plata: baja la deuda pero no
# entra a la caja ni al banco, y no cuenta como «abono» en los reportes.
MEDIO_DESCUENTO = "descuento"


def detalle_descuento(anio: int, mes: int) -> str:
    """Texto con que se asienta (y se reconoce) el descuento de un ciclo: una vez por ciclo."""
    return f"Descuento crédito familiar {mes:02d}-{anio}"


class TipoMovimientoCliente(StrEnum):
    CONSUMO = "consumo"
    ABONO = "abono"


@dataclass
class Cliente:
    nombre: str
    telefono: str = ""
    correo: str = ""
    observaciones: str = ""
    activo: bool = True
    id: int | None = None
    # CL-01: tope de lo que puede deber. None = sin cupo definido (no se limita); 0 = sin credito.
    cupo: int | None = None

    def __post_init__(self) -> None:
        if self.cupo is not None and self.cupo < 0:
            raise ReglaClienteInvalida("El cupo de crédito no puede ser negativo")
        self.nombre = " ".join(self.nombre.split())
        self.telefono = self.telefono.strip()
        self.correo = self.correo.strip()
        if not self.nombre:
            raise ReglaClienteInvalida("Falta el nombre del cliente")
        if not (self.telefono or self.correo):
            raise ReglaClienteInvalida("Falta al menos un medio de contacto (teléfono o correo)")

    @property
    def contacto(self) -> str:
        return self.telefono or self.correo


@dataclass
class MovimientoCliente:
    cliente_id: int
    tipo: TipoMovimientoCliente
    monto: int
    fecha: date
    detalle: str = ""
    medio: str | None = None  # solo abonos: efectivo / transferencia / tarjeta
    venta_uuid: str | None = None
    turno_caja_id: int | None = None  # abono en efectivo: la jornada en que entro a la gaveta
    uuid: str = field(default_factory=lambda: str(uuid4()))
    id: int | None = None

    def __post_init__(self) -> None:
        if self.monto <= 0:
            raise ReglaClienteInvalida("El monto del movimiento debe ser mayor que cero")

    @property
    def efecto(self) -> int:
        """Lo que suma (+) o resta (-) al saldo."""
        return self.monto if self.tipo is TipoMovimientoCliente.CONSUMO else -self.monto


# HU-CLI-04 (definida por la PO el 22-09-2026): al cierre del ciclo se descuenta el 20 % del
# total de consumos del mes. Ejemplo de la HU: $110.268 -> descuento $22.054 -> $88.214 a pagar.
PORCENTAJE_DESCUENTO_CREDITO = 20


def descuento_credito(consumos: int) -> int:
    """Descuento del credito familiar sobre los consumos del ciclo, al peso (medio hacia arriba)."""
    return _a_pesos(Decimal(consumos) * PORCENTAJE_DESCUENTO_CREDITO / 100)


def total_a_pagar(consumos: int) -> int:
    """Lo que paga el cliente por el ciclo: consumos menos el descuento del credito familiar."""
    return consumos - descuento_credito(consumos)


@dataclass(frozen=True)
class LineaConsumo:
    """Un producto dentro de un consumo a credito (para el estado de cuenta, HU-CLI-02/04)."""

    nombre: str
    cantidad: Decimal
    monto: int  # lo cobrado por la linea, ya con su descuento


def saldo_de(movimientos: list[MovimientoCliente]) -> int:
    return sum(m.efecto for m in movimientos)


def aviso_cupo_insuficiente(nombre: str, disponible: int, compra: int) -> str:
    """Texto unico (venta y cobro) cuando la compra a credito pasa el cupo."""
    return (
        f"El cupo de crédito de {nombre} no alcanza: le quedan {formatear_clp(disponible)} "
        f"y esta venta a crédito es de {formatear_clp(compra)}"
    )


def cupo_disponible(cupo: int | None, saldo: int) -> int | None:
    """CL-01: lo que aun puede comprar a credito (None si el cliente no tiene cupo definido).

    Pagar, sea todo o un abono, baja el saldo y por eso libera cupo.
    """
    return None if cupo is None else max(cupo - saldo, 0)


def en_ciclo(movimiento: MovimientoCliente, anio: int, mes: int) -> bool:
    return movimiento.fecha.year == anio and movimiento.fecha.month == mes


def saldo_anterior(movimientos: list[MovimientoCliente], anio: int, mes: int) -> int:
    """Saldo con que el cliente entra al ciclo (todo lo anterior al dia 1 del mes)."""
    inicio = date(anio, mes, 1)
    return saldo_de([m for m in movimientos if m.fecha < inicio])


def ultimo_consumo(movimientos: list[MovimientoCliente]) -> date | None:
    fechas = [m.fecha for m in movimientos if m.tipo is TipoMovimientoCliente.CONSUMO]
    return max(fechas) if fechas else None


def consumos_del_ciclo(movimientos: list[MovimientoCliente], anio: int, mes: int) -> int:
    return sum(
        m.monto
        for m in movimientos
        if m.tipo is TipoMovimientoCliente.CONSUMO and en_ciclo(m, anio, mes)
    )


def abonos_del_ciclo(movimientos: list[MovimientoCliente], anio: int, mes: int) -> int:
    """Lo que el cliente pago en el ciclo (el descuento asentado no es un pago)."""
    return sum(
        m.monto
        for m in movimientos
        if m.tipo is TipoMovimientoCliente.ABONO
        and m.medio != MEDIO_DESCUENTO
        and en_ciclo(m, anio, mes)
    )
