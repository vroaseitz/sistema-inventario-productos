"""Caso de uso: alertas de vencimiento con descuento sugerido (HU-INV-03, HU-INV-06).

Lista los lotes con saldo que ya vencieron o estan dentro de su ventana de aviso, del que
vence antes al que vence despues, con el descuento y el precio sugeridos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from pos.aplicacion.puertos import RepositorioLotes, RepositorioProductos
from pos.dominio.lotes import AlertaVencimiento, PoliticaDescuento

DIAS_AVISO_POR_DEFECTO = 7


@dataclass
class ConsultarAlertasVencimiento:
    repositorio_lotes: RepositorioLotes
    repositorio_productos: RepositorioProductos
    politica: PoliticaDescuento = field(default_factory=PoliticaDescuento)

    def ejecutar(self, hoy: date | None = None) -> list[AlertaVencimiento]:
        hoy = hoy or date.today()
        alertas: list[AlertaVencimiento] = []
        for lote in self.repositorio_lotes.con_saldo():
            producto = self.repositorio_productos.obtener_por_codigo(lote.codigo_producto)
            if producto is None:
                continue
            dias = lote.dias_para_vencer(hoy)
            aviso = producto.dias_aviso if producto.dias_aviso else DIAS_AVISO_POR_DEFECTO
            if dias > aviso:
                continue  # todavia lejos de vencer
            alertas.append(
                AlertaVencimiento(
                    lote=lote,
                    nombre_producto=producto.nombre,
                    precio_actual=producto.precio,
                    dias_restantes=dias,
                    descuento_pct=self.politica.porcentaje(dias, aviso),
                )
            )
        return sorted(alertas, key=lambda a: a.dias_restantes)
