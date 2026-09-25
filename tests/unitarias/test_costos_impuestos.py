# tests/unitarias/test_costos_impuestos.py

import pytest
from decimal import Decimal

# Asumimos que crearás una clase o función en tu Dominio para estos cálculos
# from pos.dominio.costos import calcular_costo_total, calcular_margen, calcular_markup

def calcular_costo_total(neto: int, tasa_iaba: Decimal = Decimal('0.0')) -> int:
    """Función de ejemplo (debería vivir en tu dominio). IVA fijo 19%."""
    iva = neto * Decimal('0.19')
    iaba = neto * tasa_iaba
    return int(neto + iva + iaba)

def calcular_margen(precio_venta: int, costo_total: int) -> Decimal:
    """Margen sobre venta: (Precio - Costo) / Precio"""
    if precio_venta <= 0:
        return Decimal('0.0')
    return ((Decimal(precio_venta) - Decimal(costo_total)) / Decimal(precio_venta)) * 100

def calcular_markup(precio_venta: int, costo_total: int) -> Decimal:
    """Markup sobre costo: (Precio - Costo) / Costo"""
    if costo_total <= 0:
        return Decimal('0.0')
    return ((Decimal(precio_venta) - Decimal(costo_total)) / Decimal(costo_total)) * 100

class TestCalculoImpuestosYRentabilidad:
    
    def test_costo_sin_impuesto_adicional(self):
        """Prueba HU-PRD-02: Costo normal solo con IVA 19%."""
        neto = 1000
        costo_total = calcular_costo_total(neto)
        # 1000 + 190 (IVA) = 1190
        assert costo_total == 1190

    def test_costo_bebida_iaba_10(self):
        """Prueba HU-PRD-02: Agua saborizada con IABA 10%."""
        neto = 1000
        costo_total = calcular_costo_total(neto, tasa_iaba=Decimal('0.10'))
        # 1000 + 190 (IVA) + 100 (IABA) = 1290
        assert costo_total == 1290

    def test_costo_energetica_iaba_18(self):
        """Prueba HU-PRD-02: Bebida energética con IABA 18%."""
        neto = 1000
        costo_total = calcular_costo_total(neto, tasa_iaba=Decimal('0.18'))
        # 1000 + 190 (IVA) + 180 (IABA) = 1370
        assert costo_total == 1370

    def test_margen_y_markup_diferenciados(self):
        """Prueba HU-PRD-03: Ambos indicadores son distintos y derivan del precio."""
        costo_total = 1000
        precio_venta = 1500
        
        margen = calcular_margen(precio_venta, costo_total)
        markup = calcular_markup(precio_venta, costo_total)
        
        # Margen: (1500 - 1000) / 1500 = 33.33%
        assert round(margen, 2) == Decimal('33.33')
        
        # Markup: (1500 - 1000) / 1000 = 50.00%
        assert round(markup, 2) == Decimal('50.00')