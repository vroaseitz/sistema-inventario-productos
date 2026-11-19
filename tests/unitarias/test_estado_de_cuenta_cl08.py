"""CL-08 y CL-06: el estado de cuenta termina en UNA cifra: «Falta pagar» o «A favor»."""

from __future__ import annotations

from pos.dominio.clientes import descuento_credito, falta_pagar, total_a_pagar
from pos.interfaz.app_clientes import _texto_deuda


def test_caso_del_qa_venta_de_11130_con_abono_de_5000():
    assert descuento_credito(11130) == 2226
    assert total_a_pagar(11130) == 8904
    assert falta_pagar(11130, 5000) == 3904  # lo que de verdad falta; no 8.904 ni 6.130


def test_sin_abonos_falta_el_total_a_pagar():
    assert falta_pagar(8990, 0) == 7192


def test_si_abono_de_mas_queda_a_favor():
    assert falta_pagar(10000, 9000) == -1000
    assert _texto_deuda(falta_pagar(10000, 9000)) == "A favor $1.000"  # CL-06: «A favor», no «−»
