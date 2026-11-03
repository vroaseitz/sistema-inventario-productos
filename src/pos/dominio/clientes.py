"""Clientes con credito y su cuenta (HU-CLI-01 a HU-CLI-05, HU-CAJ-03).

El credito es solo para familiares, segun lo definido por las propietarias. El saldo NO se guarda
en ninguna parte: se calcula sumando los movimientos (consumos suman, abonos restan). Un
movimiento registrado no se edita: un error se corrige con otro movimiento que queda a la vista.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from uuid import uuid4

from .errores import ReglaClienteInvalida

MEDIOS_ABONO = ("efectivo", "transferencia", "tarjeta")


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

    def __post_init__(self) -> None:
        self.nombre = " ".join(self.nombre.split())
        self.telefono = self.telefono.strip()
        self.correo = self.correo.strip()
        if not self.nombre:
            raise ReglaClienteInvalida("Falta el nombre del cliente")
        if not (self.telefono or self.correo):
            raise ReglaClienteInvalida("Falta al menos un medio de contacto (telefono o correo)")

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


def saldo_de(movimientos: list[MovimientoCliente]) -> int:
    return sum(m.efecto for m in movimientos)


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
    return sum(
        m.monto
        for m in movimientos
        if m.tipo is TipoMovimientoCliente.ABONO and en_ciclo(m, anio, mes)
    )
