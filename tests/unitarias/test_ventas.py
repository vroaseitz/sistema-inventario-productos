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


# --- Hallazgos QA 26-10-2026 (Hallazgos-QA_NaturalSur.xlsx) ----------------


def test_quitar_pago():
    # D-18a: se puede quitar un pago ya agregado antes de cerrar.
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(400)))
    venta.agregar_pago(Pago(medio=MedioPago.TRANSFERENCIA, monto=Dinero(600)))
    venta.quitar_pago(0)
    assert len(venta.pagos) == 1
    assert venta.pagos[0].medio is MedioPago.TRANSFERENCIA


def test_quitar_pago_indice_invalido_falla():
    venta = _venta()
    with pytest.raises(ReglaVentaInvalida):
        venta.quitar_pago(0)


def test_pago_no_efectivo_que_excede_el_saldo_se_rechaza_al_agregar():
    # D-25: antes se aceptaba un pago con tarjeta mayor al total y la venta
    # quedaba bloqueada al cerrar con un mensaje confuso; ahora se rechaza al
    # agregarlo, con un mensaje que describe el problema real.
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(5985))
    with pytest.raises(ReglaVentaInvalida):
        venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(10_000)))
    assert venta.pagos == []


def test_segundo_pago_no_efectivo_considera_lo_ya_pagado():
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(600)))
    with pytest.raises(ReglaVentaInvalida):
        # Solo quedan $400 pendientes; $500 se pasa.
        venta.agregar_pago(Pago(medio=MedioPago.TRANSFERENCIA, monto=Dinero(500)))


def test_construir_pago_efectivo_parcial_no_redondea_ni_calcula_vuelto():
    # D-18b: un efectivo menor al saldo pendiente es un pago parcial valido,
    # se registra tal cual porque falta otro pago (p. ej. tarjeta despues).
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    pago = venta.construir_pago_efectivo(monto_entregado=400)
    assert pago.monto == Dinero(400)
    assert pago.cobro_efectivo is None
    venta.agregar_pago(pago)
    assert venta.total_pagado == Dinero(400)


def test_construir_pago_efectivo_que_cubre_el_saldo_redondea_y_calcula_vuelto():
    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(400)))
    # Saldo pendiente $600; entrega $1.000 en efectivo -> vuelto $400.
    pago = venta.construir_pago_efectivo(monto_entregado=1000)
    assert pago.cobro_efectivo is not None
    assert pago.cobro_efectivo.vuelto == Dinero(400)
    venta.agregar_pago(pago)
    venta.validar_cierre()  # no lanza


def test_construir_pago_efectivo_con_composicion_por_denominacion():
    from pos.dominio.pagos import ConteoDenominaciones

    venta = _venta()
    venta.agregar_detalle("12345", 1, Dinero(1000))
    composicion = ConteoDenominaciones({1000: 1})
    pago = venta.construir_pago_efectivo(composicion=composicion)
    assert pago.monto == Dinero(1000)
    assert pago.cobro_efectivo.composicion_entregada == composicion
