"""Caso de uso: abrir la jornada de caja con un fondo inicial (HU-CAJ-01)."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import RepositorioTurnosCaja
from pos.dominio.caja import TurnoCaja
from pos.dominio.errores import ReglaCajaInvalida
from pos.dominio.pagos import ConteoDenominaciones
from pos.dominio.value_objects import Dinero


@dataclass
class AbrirTurnoCaja:
    repositorio: RepositorioTurnosCaja

    def ejecutar(
        self,
        usuario_id: int,
        fondo_inicial: Dinero,
        composicion_fondo_inicial: ConteoDenominaciones | None = None,
    ) -> TurnoCaja:
        if self.repositorio.obtener_abierto() is not None:
            raise ReglaCajaInvalida(
                "Ya hay una jornada de caja abierta; hay que cerrarla antes de abrir otra"
            )
        turno = TurnoCaja(
            usuario_id=usuario_id,
            fondo_inicial=fondo_inicial,
            composicion_fondo_inicial=composicion_fondo_inicial,
        )
        self.repositorio.guardar(turno)
        return turno
