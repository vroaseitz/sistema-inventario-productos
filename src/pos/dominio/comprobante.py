"""Comprobante de detalle y corte de caja para la impresora de 58 mm (HU-VTA-06).

El comprobante NO tiene validez tributaria: la boleta la emite el terminal de pago. Aqui solo se
arma el texto (32 caracteres de ancho); como se manda a la impresora lo resuelve la infraestructura.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from .caja import Arqueo, TurnoCaja
from .formato import formatear_clp
from .pagos import NOMBRES_MEDIO, MedioPago
from .ventas import Venta

ANCHO = 32
TIENDA = "Emporio NaturalSur"
LINEA = "-" * ANCHO


def _centrar(texto: str) -> str:
    return texto[:ANCHO].center(ANCHO).rstrip()


def _dos_columnas(izquierda: str, derecha: str) -> str:
    """Texto a la izquierda y monto a la derecha, sin pasar del ancho del papel."""
    espacio = ANCHO - len(derecha) - 1
    return f"{izquierda[:espacio]:<{espacio}} {derecha}"


def _cantidad(valor: Decimal) -> str:
    """1 -> '1'; 0.350 -> '0,350' (coma decimal, como se escribe en Chile)."""
    if valor == valor.to_integral_value():
        return str(int(valor))
    return f"{valor:f}".replace(".", ",")


def _fecha(momento: datetime) -> str:
    return momento.strftime("%d-%m-%Y %H:%M")


def comprobante_de_venta(
    venta: Venta, nombres: dict[str, str], cliente: str = "", cajera: str = ""
) -> list[str]:
    """Detalle de lo vendido, el total, como se pago y el cambio."""
    lineas = [
        _centrar(TIENDA),
        _centrar("COMPROBANTE DE DETALLE"),
        _centrar("Sin validez tributaria."),
        _centrar("La boleta la emite el terminal."),
        LINEA,
        _dos_columnas(f"Venta N° {venta.id}", _fecha(venta.creado_en)),
    ]
    if cajera:
        lineas.append(f"Atendió: {cajera}"[:ANCHO])
    lineas.append(LINEA)
    for detalle in venta.detalles:
        lineas.append(nombres.get(detalle.producto_codigo, detalle.producto_codigo)[:ANCHO])
        lineas.append(
            _dos_columnas(
                f"  {_cantidad(detalle.cantidad)} x {formatear_clp(detalle.precio_unitario.monto)}",
                formatear_clp(detalle.subtotal.monto),
            )
        )
    lineas.append(LINEA)
    lineas.append(_dos_columnas("TOTAL", formatear_clp(venta.total.monto)))
    a_cobrar = venta.total_a_cobrar.monto
    if a_cobrar != venta.total.monto:
        lineas.append(_dos_columnas("A cobrar (a la decena)", formatear_clp(a_cobrar)))
    for pago in venta.pagos:
        nombre = NOMBRES_MEDIO[pago.medio]
        if pago.cobro_efectivo is not None:
            lineas.append(
                _dos_columnas(nombre, formatear_clp(pago.cobro_efectivo.monto_entregado.monto))
            )
        else:
            lineas.append(_dos_columnas(nombre, formatear_clp(pago.monto.monto)))
        if pago.medio is MedioPago.CREDITO_CLIENTE and cliente:
            lineas.append(f"  Cuenta de {cliente}"[:ANCHO])
    if venta.vuelto_entregado.monto:
        lineas.append(_dos_columnas("Cambio", formatear_clp(venta.vuelto_entregado.monto)))
    lineas += [LINEA, _centrar("Gracias por su compra")]
    return lineas


def corte_de_caja(turno: TurnoCaja, arqueo: Arqueo, momento: datetime | None = None) -> list[str]:
    """Corte de la jornada: venta por medio de pago, partidas de caja y efectivo esperado."""
    lineas = [
        _centrar(TIENDA),
        _centrar("CORTE DE CAJA"),
        _centrar(_fecha(momento or datetime.now())),
        LINEA,
        _dos_columnas(
            f"Jornada N° {turno.id}", f"Fondo {formatear_clp(turno.fondo_inicial.monto)}"
        ),
        LINEA,
    ]
    vendido = 0
    for medio, monto in arqueo.totales_por_medio.items():
        lineas.append(_dos_columnas(NOMBRES_MEDIO[medio], formatear_clp(monto.monto)))
        vendido += monto.monto
    lineas += [
        _dos_columnas("Total vendido", formatear_clp(vendido)),
        LINEA,
        _dos_columnas("Abonos de clientes (efectivo)", formatear_clp(arqueo.abonos_efectivo.monto)),
        _dos_columnas("Ingresos de caja", formatear_clp(arqueo.ingresos_caja.monto)),
        _dos_columnas("Retiros de caja", formatear_clp(arqueo.retiros_caja.monto)),
        _dos_columnas("Cambio entregado", formatear_clp(arqueo.vuelto_entregado.monto)),
        LINEA,
        _dos_columnas("Efectivo esperado", formatear_clp(arqueo.efectivo_esperado)),
    ]
    if arqueo.efectivo_contado.monto:
        lineas += [
            _dos_columnas("Efectivo contado", formatear_clp(arqueo.efectivo_contado.monto)),
            _dos_columnas("Diferencia", formatear_clp(arqueo.diferencia)),
        ]
    return lineas


def ticket_de_prueba() -> list[str]:
    """Para comprobar la impresora y el cajon desde F7 Configuracion."""
    return [
        _centrar(TIENDA),
        _centrar("PRUEBA DE IMPRESORA"),
        LINEA,
        "Si lees esto, la impresora",
        "funciona. Ñandú, camión, 123.",
        LINEA,
    ]
