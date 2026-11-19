"""Caso de uso: registrar un retiro o ingreso de caja distinto de una venta (HU-CAJ-04)."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import ColaSincronizacion, RepositorioTurnosCaja
from pos.aplicacion.sincronizacion import encolar_movimiento
from pos.dominio.caja import MovimientoCaja, TipoMovimientoCaja
from pos.dominio.errores import ReglaCajaInvalida
from pos.dominio.value_objects import Dinero


@dataclass
class RegistrarMovimientoCaja:
    repositorio: RepositorioTurnosCaja
    cola: ColaSincronizacion | None = None

    def ejecutar(self, tipo: TipoMovimientoCaja, monto: Dinero, motivo: str) -> MovimientoCaja:
        turno = self.repositorio.obtener_abierto()
        if turno is None:
            raise ReglaCajaInvalida("No hay una jornada de caja abierta")
        movimiento = MovimientoCaja(tipo=tipo, monto=monto, motivo=motivo)
        turno.registrar_movimiento(movimiento)
        self.repositorio.registrar_movimiento(turno.id, movimiento)
        encolar_movimiento(self.cola, turno, movimiento)
        return movimiento
