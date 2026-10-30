"""Pruebas de regresion QA para el dominio de productos.

Cubre los hallazgos:
- QA C-04: categoria obligatoria.
- QA C-05a: perecible exige dias_aviso.
- QA A-02: MotivoAjuste hereda de StrEnum.
"""

from __future__ import annotations

from enum import StrEnum

import pytest

from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.inventario import MotivoAjuste
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero


def _producto_base(**overrides):
    """Producto valido base para parametrizar excepciones."""
    datos = {
        "codigo": "P-001",
        "nombre": "Producto de prueba",
        "precio": Dinero(1000),
        "categoria_id": 1,
    }
    datos.update(overrides)
    return Producto(**datos)


# --- QA C-04: categoria obligatoria -------------------------------------------


class TestCategoriaObligatoria:
    def test_producto_sin_categoria_levanta_excepcion(self):
        with pytest.raises(DatosProductoInvalidos) as excinfo:
            _producto_base(categoria_id=None)
        assert "categoria" in str(excinfo.value).lower()

    @pytest.mark.parametrize("categoria_id", [1, 2, 3, 99])
    def test_producto_con_categoria_valida_se_instancia(self, categoria_id):
        producto = _producto_base(categoria_id=categoria_id)
        assert producto.categoria_id == categoria_id


# --- QA C-05a: perecible exige dias_aviso -------------------------------------


class TestPerecibleDiasAviso:
    @pytest.mark.parametrize("dias_aviso", [None, 0, -3])
    def test_perecible_sin_dias_aviso_levanta_excepcion(self, dias_aviso):
        with pytest.raises(DatosProductoInvalidos) as excinfo:
            _producto_base(perecible=True, dias_aviso=dias_aviso)
        assert "dias_aviso" in str(excinfo.value).lower()

    def test_perecible_con_dias_aviso_valido_se_instancia(self):
        producto = _producto_base(perecible=True, dias_aviso=5)
        assert producto.perecible is True
        assert producto.dias_aviso == 5

    def test_no_perecible_permite_dias_aviso_none(self):
        producto = _producto_base(perecible=False, dias_aviso=None)
        assert producto.perecible is False
        assert producto.dias_aviso is None


# --- QA A-02: MotivoAjuste es StrEnum ------------------------------------------


class TestMotivoAjusteStrEnum:
    def test_motivo_ajuste_es_instancia_de_str(self):
        assert isinstance(MotivoAjuste.MERMA, str)

    def test_motivo_ajuste_hereda_de_strenum(self):
        assert issubclass(MotivoAjuste, StrEnum)

    def test_motivo_ajuste_compara_con_string_libre(self):
        assert MotivoAjuste.MERMA == "merma"
        assert MotivoAjuste.VENCIMIENTO == "vencimiento"
