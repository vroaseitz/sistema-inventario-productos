"""Control de existencias (stock)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from .errores import ReglaInventarioInvalida


class MotivoAjuste(StrEnum):
    """Motivos válidos para un ajuste de inventario."""

    MERMA = "merma"
    ROBO = "robo"
    VENCIMIENTO = "vencimiento"
    INVENTARIO_FISICO = "inventario_fisico"
    INGRESO_MANUAL = "ingreso_manual"
    # Motivos del prototipo v3 para «Registrar merma o ajuste» (HU-INV-04); la lista final la
    # define la Product Owner con las propietarias.
    ROTURA = "rotura"
    PERDIDA = "perdida"
    CONSUMO_INTERNO = "consumo_interno"
    DEVOLUCION = "devolucion"


@dataclass(frozen=True)
class AjusteInventario:
    """Registro inmutable de un ajuste de inventario (diferencia de conteo, merma, robo, etc.)."""

    codigo_producto: str
    cantidad_anterior: Decimal
    cantidad_nueva: Decimal
    motivo: MotivoAjuste
    usuario: str
    fecha: datetime = field(default_factory=datetime.now)
    observacion: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "cantidad_anterior", Decimal(str(self.cantidad_anterior)))
        object.__setattr__(self, "cantidad_nueva", Decimal(str(self.cantidad_nueva)))

    @property
    def diferencia_conteo(self) -> Decimal:
        """Diferencia entre la cantidad nueva contada y la cantidad anterior."""
        return self.cantidad_nueva - self.cantidad_anterior


@dataclass
class Existencia:
    """Stock de un producto.

    Se usa Decimal para soportar productos a granel (p. ej. 1.250 kg). Para productos
    por unidad, la cantidad sera un entero representado como Decimal.
    """

    codigo_producto: str
    cantidad: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        self.cantidad = Decimal(str(self.cantidad))
        if self.cantidad < 0:
            raise ReglaInventarioInvalida("El stock inicial no puede ser negativo")

    def ingresar(self, cantidad: Decimal) -> None:
        cantidad = Decimal(str(cantidad))
        if cantidad <= 0:
            raise ReglaInventarioInvalida("El ingreso debe ser mayor que cero")
        self.cantidad += cantidad

    def descontar(self, cantidad: Decimal) -> None:
        cantidad = Decimal(str(cantidad))
        if cantidad <= 0:
            raise ReglaInventarioInvalida("El descuento debe ser mayor que cero")
        if cantidad > self.cantidad:
            raise ReglaInventarioInvalida(
                f"Stock insuficiente: hay {self.cantidad}, se piden {cantidad}"
            )
        self.cantidad -= cantidad


# Como se le muestra cada motivo a las usuarias (reporte de movimientos, auditoria).
ETIQUETAS_MOTIVO = {
    MotivoAjuste.MERMA: "Merma",
    MotivoAjuste.ROBO: "Robo",
    MotivoAjuste.VENCIMIENTO: "Vencimiento",
    MotivoAjuste.INVENTARIO_FISICO: "Inventario físico",
    MotivoAjuste.INGRESO_MANUAL: "Ingreso manual",
    MotivoAjuste.ROTURA: "Rotura",
    MotivoAjuste.PERDIDA: "Pérdida",
    MotivoAjuste.CONSUMO_INTERNO: "Consumo interno",
    MotivoAjuste.DEVOLUCION: "Devolución",
}


class TipoMovimiento(StrEnum):
    ENTRADA = "entrada"
    VENTA = "venta"
    MERMA = "merma"
    AJUSTE = "ajuste"
    ANULACION = "anulacion"  # HU-VTA-11: lo vendido vuelve a la existencia


@dataclass
class MovimientoInventario:
    """Una linea del historial: de donde salio o entro la mercaderia (HU-INV-08).

    `cantidad` lleva signo: positiva entra, negativa sale. No se edita nunca: un error se corrige
    con otro movimiento que queda a la vista.
    """

    codigo_producto: str
    tipo: TipoMovimiento
    cantidad: Decimal
    motivo: str = ""
    usuario: str = ""
    fecha: datetime = field(default_factory=datetime.now)
    id: int | None = None

    def __post_init__(self) -> None:
        self.cantidad = Decimal(str(self.cantidad))


ESTADO_AGOTADO = "Agotado"
ESTADO_BAJO_MINIMO = "Bajo el mínimo"
ESTADO_NORMAL = "Normal"
ESTADO_GRANEL = "Granel"


def estado_de_existencia(cantidad: Decimal, minimo: int | None, granel: bool) -> str:
    """Agotado, bajo el minimo, normal o granel (el granel se muestra aparte, en kilos)."""
    if granel:
        return ESTADO_GRANEL
    if cantidad <= 0:
        return ESTADO_AGOTADO
    if minimo is not None and cantidad < minimo:
        return ESTADO_BAJO_MINIMO
    return ESTADO_NORMAL
