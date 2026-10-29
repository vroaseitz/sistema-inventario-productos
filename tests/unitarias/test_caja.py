"""Pruebas de turno de caja, movimientos y arqueo de cierre.

Cubre HU-CAJ-01 (apertura con fondo inicial), HU-CAJ-04 (movimientos distintos
de la venta) y HU-CAJ-02/03 (arqueo: efectivo esperado y diferencia).
"""

import pytest

from pos.dominio.caja import MovimientoCaja, TipoMovimientoCaja, TurnoCaja, calcular_arqueo
from pos.dominio.errores import ReglaCajaInvalida
from pos.dominio.pagos import MedioPago, Pago, calcular_cobro_efectivo
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import Venta


def test_turno_abre_con_fondo_inicial():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    assert turno.esta_abierto
    assert turno.fondo_inicial == Dinero(15_000)


def test_cerrar_turno_lo_marca_cerrado():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    turno.cerrar()
    assert not turno.esta_abierto
    assert turno.cerrado_en is not None


def test_no_se_puede_cerrar_un_turno_ya_cerrado():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    turno.cerrar()
    with pytest.raises(ReglaCajaInvalida):
        turno.cerrar()


def test_movimiento_de_caja_exige_motivo():
    # HU-CAJ-04: el motivo es obligatorio y se elige de una lista definida.
    with pytest.raises(ReglaCajaInvalida):
        MovimientoCaja(tipo=TipoMovimientoCaja.RETIRO, monto=Dinero(5000), motivo="")


def test_no_se_pueden_registrar_movimientos_en_turno_cerrado():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    turno.cerrar()
    with pytest.raises(ReglaCajaInvalida):
        turno.registrar_movimiento(
            MovimientoCaja(tipo=TipoMovimientoCaja.INGRESO, monto=Dinero(1000), motivo="vuelto")
        )


def _venta_pagada_en_efectivo(total: int, entregado: int) -> Venta:
    venta = Venta(turno_caja_id=1, usuario_id=1)
    venta.agregar_detalle("12345", 1, Dinero(total))
    cobro = calcular_cobro_efectivo(venta.total, monto_entregado=Dinero(entregado))
    pago = Pago(medio=MedioPago.EFECTIVO, monto=cobro.total_redondeado, cobro_efectivo=cobro)
    venta.agregar_pago(pago)
    return venta


def test_arqueo_sin_movimientos_ni_ventas_iguala_el_fondo_inicial():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    arqueo = calcular_arqueo(turno, ventas=[], efectivo_contado=Dinero(15_000))
    assert arqueo.efectivo_esperado == 15_000
    assert arqueo.diferencia == 0


def test_arqueo_suma_ventas_en_efectivo_al_esperado():
    # HU-CAJ-02: el efectivo esperado es fondo inicial + ventas en efectivo
    # (+ abonos + ingresos - retiros - vuelto entregado).
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    venta = _venta_pagada_en_efectivo(total=5000, entregado=5000)
    arqueo = calcular_arqueo(turno, ventas=[venta], efectivo_contado=Dinero(20_000))
    assert arqueo.totales_por_medio[MedioPago.EFECTIVO] == Dinero(5000)
    assert arqueo.efectivo_esperado == 20_000
    assert arqueo.diferencia == 0


def test_arqueo_descuenta_el_vuelto_entregado():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(0))
    venta = _venta_pagada_en_efectivo(total=1000, entregado=2000)  # vuelto $1.000
    arqueo = calcular_arqueo(turno, ventas=[venta], efectivo_contado=Dinero(1000))
    assert arqueo.vuelto_entregado == Dinero(1000)
    assert arqueo.efectivo_esperado == 1000
    assert arqueo.diferencia == 0


def test_arqueo_resta_retiros_y_suma_ingresos():
    # HU-CAJ-04: los movimientos de caja afectan el efectivo esperado del arqueo.
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    turno.registrar_movimiento(
        MovimientoCaja(
            tipo=TipoMovimientoCaja.RETIRO, monto=Dinero(3000), motivo="pago a proveedor"
        )
    )
    turno.registrar_movimiento(
        MovimientoCaja(tipo=TipoMovimientoCaja.INGRESO, monto=Dinero(1000), motivo="cambio chico")
    )
    arqueo = calcular_arqueo(turno, ventas=[], efectivo_contado=Dinero(13_000))
    assert arqueo.efectivo_esperado == 15_000 - 3000 + 1000
    assert arqueo.diferencia == 0


def test_arqueo_detecta_faltante():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(15_000))
    arqueo = calcular_arqueo(turno, ventas=[], efectivo_contado=Dinero(14_500))
    assert arqueo.diferencia == -500


def test_arqueo_no_cuenta_tarjeta_como_efectivo():
    turno = TurnoCaja(usuario_id=1, fondo_inicial=Dinero(0))
    venta = Venta(turno_caja_id=1, usuario_id=1)
    venta.agregar_detalle("12345", 1, Dinero(5000))
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(5000)))
    arqueo = calcular_arqueo(turno, ventas=[venta], efectivo_contado=Dinero(0))
    assert arqueo.totales_por_medio[MedioPago.TARJETA] == Dinero(5000)
    assert arqueo.totales_por_medio[MedioPago.EFECTIVO] == Dinero(0)
    assert arqueo.efectivo_esperado == 0
