"""Pruebas de medios de pago, redondeo en efectivo y conteo por denominacion.

Cubre HU-VTA-03 (medios de pago) y HU-VTA-04 (cobro en efectivo con redondeo,
vuelto y detalle por denominacion).
"""

import pytest

from pos.dominio.errores import ReglaVentaInvalida
from pos.dominio.pagos import (
    ConteoDenominaciones,
    MedioPago,
    Pago,
    calcular_cobro_efectivo,
    redondear_a_decena,
)
from pos.dominio.value_objects import Dinero


def test_redondeo_a_decena_hacia_arriba():
    assert redondear_a_decena(1236) == 1240


def test_redondeo_a_decena_hacia_abajo():
    assert redondear_a_decena(1234) == 1230


def test_redondeo_exacto_en_cinco_va_hacia_abajo():
    # HU-VTA-04: cuando el total termina en 5, se redondea hacia abajo, a favor
    # del cliente.
    assert redondear_a_decena(1235) == 1230


def test_redondeo_multiplo_de_diez_no_cambia():
    assert redondear_a_decena(1230) == 1230


def test_cobro_efectivo_calcula_vuelto_sobre_total_redondeado():
    cobro = calcular_cobro_efectivo(Dinero(1235), monto_entregado=Dinero(2000))
    assert cobro.total_redondeado == Dinero(1230)
    assert cobro.diferencia_redondeo == -5
    assert cobro.vuelto == Dinero(770)


def test_cobro_efectivo_con_composicion_suma_sola():
    composicion = ConteoDenominaciones({10_000: 1, 1_000: 1})  # $11.000
    cobro = calcular_cobro_efectivo(Dinero(1235), composicion=composicion)
    assert cobro.monto_entregado == Dinero(11_000)
    assert cobro.vuelto == Dinero(11_000 - 1230)


def test_cobro_efectivo_entregado_insuficiente_falla():
    with pytest.raises(ReglaVentaInvalida):
        calcular_cobro_efectivo(Dinero(5000), monto_entregado=Dinero(4000))


def test_cobro_efectivo_exige_uno_de_entregado_o_composicion():
    with pytest.raises(ReglaVentaInvalida):
        calcular_cobro_efectivo(Dinero(1000))
    with pytest.raises(ReglaVentaInvalida):
        calcular_cobro_efectivo(
            Dinero(1000), monto_entregado=Dinero(1000), composicion=ConteoDenominaciones({1000: 1})
        )


def test_conteo_denominaciones_rechaza_valor_no_vigente():
    with pytest.raises(ReglaVentaInvalida):
        ConteoDenominaciones({25: 1})


def test_conteo_denominaciones_rechaza_cantidad_negativa():
    with pytest.raises(ReglaVentaInvalida):
        ConteoDenominaciones({1000: -1})


def test_pago_no_efectivo_no_admite_detalle_de_cobro():
    cobro = calcular_cobro_efectivo(Dinero(1000), monto_entregado=Dinero(1000))
    with pytest.raises(ReglaVentaInvalida):
        Pago(medio=MedioPago.TARJETA, monto=Dinero(1000), cobro_efectivo=cobro)


def test_pago_efectivo_monto_debe_coincidir_con_redondeado():
    cobro = calcular_cobro_efectivo(Dinero(1235), monto_entregado=Dinero(2000))
    with pytest.raises(ReglaVentaInvalida):
        Pago(medio=MedioPago.EFECTIVO, monto=Dinero(1235), cobro_efectivo=cobro)
    # El monto correcto (ya redondeado) no falla:
    Pago(medio=MedioPago.EFECTIVO, monto=Dinero(1230), cobro_efectivo=cobro)
