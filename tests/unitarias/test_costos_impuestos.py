"""Pruebas de costos, impuestos y rentabilidad (HU-PRD-02 y HU-PRD-03)."""

from __future__ import annotations

from decimal import Decimal

from pos.dominio.productos import Producto
from pos.dominio.value_objects import Costo, Dinero


class TestCalculoImpuestosYRentabilidad:
    def test_costo_sin_impuesto_adicional(self):
        """Prueba HU-PRD-02: Costo normal solo con IVA 19%."""
        neto = Dinero(1000)
        iva = Dinero(190)  # 19% de 1000
        costo = Costo(neto=neto, iva=iva)

        # 1000 + 190 (IVA) = 1190
        assert costo.total == Dinero(1190)

    def test_costo_bebida_iaba_10(self):
        """Prueba HU-PRD-02: Agua saborizada o bebida con IABA 10% e IVA 19%."""
        neto = Dinero(1000)
        iva = Dinero(190)
        iaba = Dinero(100)  # 10% de 1000
        costo = Costo(neto=neto, iva=iva, impuesto_adicional=iaba)

        # 1000 + 190 (IVA) + 100 (IABA) = 1290
        assert costo.total == Dinero(1290)

    def test_costo_energetica_iaba_18(self):
        """Prueba HU-PRD-02: Bebida energética con IABA 18% e IVA 19%."""
        neto = Dinero(1000)
        iva = Dinero(190)
        iaba = Dinero(180)  # 18% de 1000
        costo = Costo(neto=neto, iva=iva, impuesto_adicional=iaba)

        # 1000 + 190 (IVA) + 180 (IABA) = 1370
        assert costo.total == Dinero(1370)

    def test_margen_y_markup_diferenciados(self):
        """Prueba HU-PRD-03: Ambos indicadores son distintos y derivan del precio y costo neto."""
        costo = Costo(neto=Dinero(1000), iva=Dinero(190))
        producto = Producto(
            codigo="12345",
            nombre="Bebida Isotónica",
            precio=Dinero(1500),
            costo=costo,
        )

        # Margen sobre venta: (1500 - 1000) / 1500 = 0.3333 (33.33%)
        assert producto.margen == Decimal("0.3333")

        # Markup sobre costo: (1500 - 1000) / 1000 = 0.5000 (50.00%)
        assert producto.markup == Decimal("0.5000")
