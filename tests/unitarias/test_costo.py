"""Pruebas del value object Costo (HU-PRD-02: neto, IVA e impuesto adicional separados)."""

from pos.dominio.value_objects import Costo, Dinero


def test_costo_total_suma_los_tres_componentes():
    costo = Costo(neto=Dinero(1000), iva=Dinero(190), impuesto_adicional=Dinero(50))
    assert costo.total.monto == 1240


def test_costo_sin_impuesto_adicional_por_defecto():
    costo = Costo(neto=Dinero(1000), iva=Dinero(190))
    assert costo.impuesto_adicional.monto == 0
    assert costo.total.monto == 1190


def test_costo_guarda_neto_sin_impuesto_incluido():
    # El neto se guarda tal cual se ingresa, no se deriva a partir del total.
    costo = Costo(neto=Dinero(1000), iva=Dinero(190))
    assert costo.neto.monto == 1000
