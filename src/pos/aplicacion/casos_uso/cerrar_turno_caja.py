"""Caso de uso: cerrar la jornada de caja con arqueo (HU-CAJ-02, HU-CAJ-03)."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioClientes,
    RepositorioTurnosCaja,
    RepositorioVentas,
)
from pos.aplicacion.sincronizacion import encolar_turno_cerrado
from pos.dominio.caja import Arqueo, calcular_arqueo
from pos.dominio.errores import ReglaCajaInvalida
from pos.dominio.value_objects import Dinero


@dataclass
class CerrarTurnoCaja:
    repositorio_turnos: RepositorioTurnosCaja
    repositorio_ventas: RepositorioVentas
    cola: ColaSincronizacion | None = None
    repositorio_clientes: RepositorioClientes | None = None

    def ejecutar(
        self,
        efectivo_contado: Dinero,
        abonos_efectivo: Dinero | None = None,
    ) -> Arqueo:
        turno = self.repositorio_turnos.obtener_abierto()
        if turno is None:
            raise ReglaCajaInvalida("No hay una jornada de caja abierta para cerrar")

        ventas = self.repositorio_ventas.obtener_por_turno(turno.id)
        if abonos_efectivo is None and self.repositorio_clientes is not None:
            # HU-CAJ-03: los abonos de clientes en efectivo entran a la gaveta, no son venta.
            abonos_efectivo = Dinero(
                self.repositorio_clientes.abonos_en_efectivo_del_turno(turno.id)
            )
        arqueo = calcular_arqueo(turno, ventas, efectivo_contado, abonos_efectivo=abonos_efectivo)

        turno.cerrar()
        self.repositorio_turnos.guardar(turno)
        encolar_turno_cerrado(self.cola, turno)
        return arqueo
