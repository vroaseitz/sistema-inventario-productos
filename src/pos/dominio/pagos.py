"""Medios de pago, redondeo en efectivo y conteo por denominacion.

Reglas tomadas del Product Backlog v4.3 (HU-VTA-03, HU-VTA-04):

- Los medios son efectivo, tarjeta, transferencia y credito de cliente. La tarjeta
  se registra como un unico medio: el terminal TUU no distingue debito de credito,
  asi que pedirle esa distincion a quien cobra seria pedirle un dato que no tiene.
- El redondeo a la decena se aplica solo sobre la porcion pagada en efectivo, nunca
  sobre tarjeta ni transferencia. Si el total termina en 5, se redondea hacia abajo,
  a favor del cliente (no hay moneda de 5 pesos en circulacion).
- El vuelto es monto entregado menos el total ya redondeado.
- El detalle por denominacion es opcional: si no se entrega, solo se guarda el
  monto entregado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .errores import ReglaVentaInvalida
from .value_objects import Dinero

# Denominaciones de curso vigente en Chile (billetes y monedas de uso habitual;
# se excluyen las monedas de $1 y $5, retiradas de circulacion activa).
DENOMINACIONES_CLP: tuple[int, ...] = (20_000, 10_000, 5_000, 2_000, 1_000, 500, 100, 50, 10)


class MedioPago(Enum):
    """Medios de pago admitidos por una venta (HU-VTA-03)."""

    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"
    CREDITO_CLIENTE = "credito_cliente"


def redondear_a_decena(monto: int) -> int:
    """Redondea un monto en pesos a la decena mas cercana.

    Politica de negocio (HU-VTA-04), distinta de la politica HALF_UP de `Dinero`:
    cuando el resto es exactamente 5, se redondea hacia ABAJO, a favor del cliente.
    """
    resto = monto % 10
    if resto <= 5:
        return monto - resto
    return monto + (10 - resto)


@dataclass(frozen=True)
class ConteoDenominaciones:
    """Conteo de billetes/monedas entregados o contados, por denominacion.

    `conteo` mapea denominacion (una de `DENOMINACIONES_CLP`) a la cantidad de
    piezas de ese valor.
    """

    conteo: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for denominacion, cantidad in self.conteo.items():
            if denominacion not in DENOMINACIONES_CLP:
                raise ReglaVentaInvalida(f"Denominacion no reconocida: {denominacion}")
            if cantidad < 0:
                raise ReglaVentaInvalida("La cantidad de piezas no puede ser negativa")

    @property
    def total(self) -> int:
        return sum(denominacion * cantidad for denominacion, cantidad in self.conteo.items())


@dataclass(frozen=True)
class CobroEfectivo:
    """Detalle completo de un cobro en efectivo, para auditoria y arqueo."""

    total_sin_redondear: Dinero
    total_redondeado: Dinero
    diferencia_redondeo: int
    monto_entregado: Dinero
    vuelto: Dinero
    composicion_entregada: ConteoDenominaciones | None = None


def calcular_cobro_efectivo(
    total: Dinero,
    *,
    monto_entregado: Dinero | None = None,
    composicion: ConteoDenominaciones | None = None,
) -> CobroEfectivo:
    """Calcula redondeo, vuelto y diferencia de un cobro en efectivo (HU-VTA-04).

    Se entrega exactamente uno de `monto_entregado` o `composicion`: si se detalla
    por denominacion, el monto entregado se suma solo a partir de esa composicion.
    """
    if (monto_entregado is None) == (composicion is None):
        raise ReglaVentaInvalida(
            "Se debe indicar el monto entregado o su composicion por denominacion, "
            "no ambos ni ninguno"
        )

    entregado = Dinero(composicion.total) if composicion is not None else monto_entregado
    assert entregado is not None  # garantizado por la validacion anterior

    redondeado = redondear_a_decena(total.monto)
    if entregado.monto < redondeado:
        raise ReglaVentaInvalida(
            f"El monto entregado (${entregado.monto}) es menor "
            f"que el total a cobrar (${redondeado})"
        )

    return CobroEfectivo(
        total_sin_redondear=total,
        total_redondeado=Dinero(redondeado),
        diferencia_redondeo=redondeado - total.monto,
        monto_entregado=entregado,
        vuelto=Dinero(entregado.monto - redondeado),
        composicion_entregada=composicion,
    )


@dataclass(frozen=True)
class Pago:
    """Un pago asociado a una venta.

    `monto` es siempre lo que efectivamente cubre del total (para efectivo, ya
    redondeado a la decena); el detalle de cuanto entrego el cliente y el vuelto
    vive en `cobro_efectivo`, solo presente cuando `medio` es EFECTIVO.
    """

    medio: MedioPago
    monto: Dinero
    cobro_efectivo: CobroEfectivo | None = None

    def __post_init__(self) -> None:
        if self.medio is not MedioPago.EFECTIVO and self.cobro_efectivo is not None:
            raise ReglaVentaInvalida("Solo un pago en efectivo puede traer detalle de cobro")
        if (
            self.medio is MedioPago.EFECTIVO
            and self.cobro_efectivo is not None
            and self.monto.monto != self.cobro_efectivo.total_redondeado.monto
        ):
            raise ReglaVentaInvalida(
                "El monto del pago en efectivo debe coincidir con el total ya redondeado"
            )
