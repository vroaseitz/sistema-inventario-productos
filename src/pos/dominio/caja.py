"""Turno de caja, movimientos y arqueo de cierre (HU-CAJ-01, 02, 03, 04).

Una jornada de caja (`TurnoCaja`) se abre con un fondo inicial y se cierra con un
arqueo que compara el efectivo contado contra el efectivo esperado:

    esperado = fondo_inicial + ventas_en_efectivo + abonos_de_clientes_en_efectivo
               + ingresos_de_caja - retiros_de_caja - vuelto_entregado

Los abonos de clientes a credito (HU-CAJ-03) dependen del modulo de credito
(HU-CLI-01/02), que todavia no existe en este incremento: se deja el parametro
listo (`abonos_efectivo`) para cuando ese modulo se construya, y por ahora se
asume cero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .errores import ReglaCajaInvalida
from .pagos import ConteoDenominaciones, MedioPago
from .value_objects import Dinero
from .ventas import EstadoVenta, Venta


class TipoMovimientoCaja(Enum):
    """Movimientos de caja que no son una venta (HU-CAJ-04)."""

    RETIRO = "retiro"
    INGRESO = "ingreso"


@dataclass(frozen=True)
class MovimientoCaja:
    tipo: TipoMovimientoCaja
    monto: Dinero
    motivo: str
    creado_en: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.motivo or not self.motivo.strip():
            raise ReglaCajaInvalida("El movimiento de caja requiere un motivo")


@dataclass
class TurnoCaja:
    usuario_id: int
    fondo_inicial: Dinero
    composicion_fondo_inicial: ConteoDenominaciones | None = None
    abierto_en: datetime = field(default_factory=datetime.now)
    cerrado_en: datetime | None = None
    movimientos: list[MovimientoCaja] = field(default_factory=list)

    @property
    def esta_abierto(self) -> bool:
        return self.cerrado_en is None

    def registrar_movimiento(self, movimiento: MovimientoCaja) -> None:
        if not self.esta_abierto:
            raise ReglaCajaInvalida("No se pueden registrar movimientos en una jornada cerrada")
        self.movimientos.append(movimiento)

    def cerrar(self, fecha: datetime | None = None) -> None:
        if not self.esta_abierto:
            raise ReglaCajaInvalida("La jornada ya esta cerrada")
        self.cerrado_en = fecha or datetime.now()


@dataclass(frozen=True)
class Arqueo:
    """Resultado del cierre de una jornada (HU-CAJ-02, HU-CAJ-03).

    `diferencia` es un entero (no `Dinero`): un faltante de caja es un numero
    negativo legitimo, y `Dinero` no admite montos negativos.
    """

    totales_por_medio: dict[MedioPago, Dinero]
    abonos_efectivo: Dinero
    ingresos_caja: Dinero
    retiros_caja: Dinero
    vuelto_entregado: Dinero
    efectivo_contado: Dinero
    efectivo_esperado: int
    diferencia: int


def calcular_arqueo(
    turno: TurnoCaja,
    ventas: list[Venta],
    efectivo_contado: Dinero,
    *,
    abonos_efectivo: Dinero | None = None,
) -> Arqueo:
    """Calcula el arqueo de cierre de una jornada.

    Solo se consideran las ventas con estado PAGADA: una venta anulada no aporta
    al total vendido ni al efectivo esperado (HU-VTA-11, fuera de este incremento
    pero la regla ya se respeta aqui).
    """
    abonos = abonos_efectivo if abonos_efectivo is not None else Dinero(0)
    totales_por_medio: dict[MedioPago, int] = dict.fromkeys(MedioPago, 0)
    efectivo_entregado_total = 0
    vuelto_total = 0
    for venta in ventas:
        if venta.estado is not EstadoVenta.PAGADA:
            continue
        for pago in venta.pagos:
            # totales_por_medio es la VENTA (neta del vuelto): lo que se compara
            # contra el reporte del terminal de pago, no el flujo de caja.
            totales_por_medio[pago.medio] += pago.monto.monto
            if pago.cobro_efectivo is not None:
                efectivo_entregado_total += pago.cobro_efectivo.monto_entregado.monto
        vuelto_total += venta.vuelto_entregado.monto

    ingresos = sum(
        m.monto.monto for m in turno.movimientos if m.tipo is TipoMovimientoCaja.INGRESO
    )
    retiros = sum(m.monto.monto for m in turno.movimientos if m.tipo is TipoMovimientoCaja.RETIRO)

    # El efectivo esperado sigue el flujo de caja real: lo que el cliente entrego
    # en mano (bruto) menos el vuelto que salio de la gaveta, no la venta neta ya
    # descontada (que es `totales_por_medio[EFECTIVO]`, para otro proposito).
    efectivo_esperado = (
        turno.fondo_inicial.monto
        + efectivo_entregado_total
        + abonos.monto
        + ingresos
        - retiros
        - vuelto_total
    )

    return Arqueo(
        totales_por_medio={medio: Dinero(monto) for medio, monto in totales_por_medio.items()},
        abonos_efectivo=abonos,
        ingresos_caja=Dinero(ingresos),
        retiros_caja=Dinero(retiros),
        vuelto_entregado=Dinero(vuelto_total),
        efectivo_contado=efectivo_contado,
        efectivo_esperado=efectivo_esperado,
        diferencia=efectivo_contado.monto - efectivo_esperado,
    )
