"""Pruebas de la entidad Venta: lineas, totales y cierre con pagos combinados.

Cubre HU-VTA-01 (acumular lineas sin duplicar), HU-VTA-03 (medios de pago
combinados) y HU-VTA-04 (redondeo solo si hay un pago en efectivo).
"""

from decimal import Decimal

import pytest

from pos.dominio.errores import ReglaVentaInvalida
from pos.dominio.pagos import MedioPago, Pago, calcular_cobro_efectivo
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import Venta


def _venta() -> Venta:
    return Venta(turno_caja_id=1, usuario_id=1)


def test_agregar_detalle_nuevo_producto():
    venta = _venta()
    venta.agregar_detalle("12345", Decimal("2"), Dinero(1000))
    assert venta.total == Dinero(2000)


def test_agregar_el_mismo_producto_dos_veces_suma_cantidad():
    # HU-VTA-01: leer dos veces el mismo producto incrementa la cantidad en
    # lugar de duplicar la linea.
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    venta.agregar_detalle("12345", 1, Dinero(1000))
    assert len(venta.detalles) == 1
    assert venta.detalles[0].cantidad == Decimal("2")
    assert venta.total == Dinero(2000)


def test_quitar_detalle():
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    venta.quitar_detalle("12345")
    assert venta.detalles == []


def test_quitar_detalle_inexistente_falla():
    venta = _venta()
    with pytest.raises(ReglaVentaInvalida):
        venta.quitar_detalle("nope")


def test_cantidad_cero_o_negativa_falla():
    venta = _venta()
    with pytest.raises(ReglaVentaInvalida):
        venta.agregar_detalle("12345", 0, Dinero(1000))


def test_cerrar_venta_sin_productos_falla():
    venta = _venta()
    with pytest.raises(ReglaVentaInvalida):
        venta.validar_cierre()


def test_cerrar_venta_sin_pagos_falla():
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    with pytest.raises(ReglaVentaInvalida):
        venta.validar_cierre()


def test_pago_unico_con_tarjeta_no_redondea():
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1235))
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(1235)))
    assert venta.total_a_cobrar == Dinero(1235)
    venta.validar_cierre()  # no lanza


def test_pago_en_efectivo_redondea_el_total_a_cobrar():
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1235))
    cobro = calcular_cobro_efectivo(venta.total, monto_entregado=Dinero(2000))
    pago = Pago(medio=MedioPago.EFECTIVO, monto=cobro.total_redondeado, cobro_efectivo=cobro)
    venta.agregar_pago(pago)
    assert venta.total_a_cobrar == Dinero(1230)
    venta.validar_cierre()  # no lanza
    assert venta.vuelto_entregado == Dinero(770)


def test_pago_combinado_tarjeta_y_efectivo_cubre_el_resto_redondeado():
    # HU-VTA-03: una misma venta admite pago combinado y la suma debe igualar
    # el total (redondeado, porque hay un pago en efectivo).
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(2235))
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(2000)))
    resto = Dinero(venta.total.monto - 2000)  # $235 a cubrir en efectivo
    cobro = calcular_cobro_efectivo(resto, monto_entregado=Dinero(300))
    venta.agregar_pago(
        Pago(medio=MedioPago.EFECTIVO, monto=cobro.total_redondeado, cobro_efectivo=cobro)
    )
    venta.validar_cierre()  # no lanza: 2000 + 230 == redondear_a_decena(2235) == 2230


def test_pago_insuficiente_no_permite_cerrar():
    # HU-VTA-03: el sistema no permite cerrar la venta si la suma de los pagos
    # no cubre el total.
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(500)))
    with pytest.raises(ReglaVentaInvalida):
        venta.validar_cierre()


def test_descuento_de_linea_se_resta_del_subtotal():
    venta = _venta()
    detalle = venta.agregar_detalle("12345", 2, Dinero(1000))
    detalle.descuento_linea = Dinero(300)
    assert detalle.subtotal == Dinero(1700)
    assert venta.total == Dinero(1700)


def test_descuento_de_linea_no_puede_superar_el_bruto():
    venta = _venta()
    detalle = venta.agregar_detalle("12345", 1, Dinero(500))
    detalle.descuento_linea = Dinero(600)
    with pytest.raises(ReglaVentaInvalida):
        _ = detalle.subtotal
