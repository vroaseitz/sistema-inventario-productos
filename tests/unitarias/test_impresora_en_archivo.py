"""A-12: dos comprobantes seguidos nunca se pisan, aunque el reloj devuelva la misma hora."""

from __future__ import annotations

from datetime import datetime

from pos.infraestructura.impresion import impresoras
from pos.infraestructura.impresion.impresoras import ImpresoraEnArchivo


def test_comprobantes_con_la_misma_hora_no_se_sobrescriben(tmp_path, monkeypatch):
    class RelojQuieto:
        @staticmethod
        def now():
            return datetime(2026, 11, 18, 12, 0, 0, 0)  # el reloj de Windows no avanza

    monkeypatch.setattr(impresoras, "datetime", RelojQuieto)
    carpeta = tmp_path / "comprobantes"
    for i in range(5):
        ImpresoraEnArchivo(carpeta).imprimir([f"venta {i}"])  # una impresora nueva cada vez

    archivos = sorted(carpeta.glob("comprobante-*.txt"))
    assert len(archivos) == 5
    assert [a.read_text(encoding="utf-8").strip() for a in archivos] == [
        f"venta {i}" for i in range(5)
    ]  # y el orden alfabetico es el de impresion
