"""Caso de uso: «Resumen del dia» al abrir el sistema (HU-REP-01 y HU-REP-05).

Venta de hoy y de la semana, ganancia de hoy, cumplimiento de la meta diaria, venta por medio de
pago, los productos que mas ganancia aportan y lo que necesita atencion (lotes por vencer,
productos bajo el minimo y productos sin costo cargado).

La meta es de GANANCIA (no de monto vendido) y depende del tipo de dia. Las metas reales salen del
Excel de punto de equilibrio de la Product Owner, que todavia no se entrega: sin meta cargada el
cumplimiento no se calcula (no se inventa un valor).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento
from pos.aplicacion.casos_uso.consultar_inventario import ConsultarExistencias
from pos.aplicacion.casos_uso.reporte_rentabilidad import FilaRentabilidad, ReporteRentabilidad
from pos.aplicacion.puertos import RepositorioConfiguracion, RepositorioProductos, RepositorioVentas
from pos.dominio.inventario import ESTADO_AGOTADO, ESTADO_BAJO_MINIMO
from pos.dominio.pagos import MedioPago

# Clave de la meta (en la configuracion) segun el dia de la semana: 0 = lunes ... 6 = domingo.
TIPOS_DE_DIA = (
    ("meta_lunes_viernes", "Lunes a viernes"),
    ("meta_sabado", "Sábado"),
    ("meta_domingo", "Domingo y festivos"),
)


def clave_de_meta(dia: date) -> str:
    if dia.weekday() == 6:
        return "meta_domingo"
    return "meta_sabado" if dia.weekday() == 5 else "meta_lunes_viernes"


@dataclass(frozen=True)
class Aviso:
    titulo: str
    detalle: str
    destino: str  # a que pantalla lleva: alertas, existencias o productos
    urgente: bool = False


@dataclass(frozen=True)
class ResumenDia:
    venta_hoy: int
    transacciones: int
    venta_semana: int
    jornadas_semana: int
    ganancia_hoy: int
    margen_hoy: float | None
    meta: int
    cumplimiento: float | None  # ganancia de hoy / meta; None si no hay meta cargada
    por_medio: dict[MedioPago, tuple[int, int]]  # medio -> (monto, cantidad de ventas)
    mayor_ganancia: list[FilaRentabilidad]
    avisos: list[Aviso] = field(default_factory=list)


@dataclass
class ResumenDelDia:
    repositorio_ventas: RepositorioVentas
    repositorio_productos: RepositorioProductos
    reporte_rentabilidad: ReporteRentabilidad
    alertas: ConsultarAlertasVencimiento
    existencias: ConsultarExistencias
    configuracion: RepositorioConfiguracion

    def ejecutar(self, hoy: date | None = None) -> ResumenDia:
        hoy = hoy or date.today()
        ventas_hoy = self.repositorio_ventas.por_periodo(hoy, hoy)
        lunes = hoy - timedelta(days=hoy.weekday())
        ventas_semana = self.repositorio_ventas.por_periodo(lunes, hoy)
        por_medio: dict[MedioPago, tuple[int, int]] = dict.fromkeys(MedioPago, (0, 0))
        for venta in ventas_hoy:
            for medio in {p.medio for p in venta.pagos}:
                monto = sum(p.monto.monto for p in venta.pagos if p.medio is medio)
                total, cantidad = por_medio[medio]
                por_medio[medio] = (total + monto, cantidad + 1)

        rentabilidad = self.reporte_rentabilidad.ejecutar(hoy, hoy)
        meta = self.configuracion.obtener(clave_de_meta(hoy))
        return ResumenDia(
            venta_hoy=sum(v.total_pagado.monto for v in ventas_hoy),
            transacciones=len(ventas_hoy),
            venta_semana=sum(v.total_pagado.monto for v in ventas_semana),
            jornadas_semana=len({v.creado_en.date() for v in ventas_semana}),
            ganancia_hoy=rentabilidad.ganancia_total,
            margen_hoy=rentabilidad.margen_total,
            meta=meta,
            cumplimiento=rentabilidad.ganancia_total / meta if meta else None,
            por_medio=por_medio,
            mayor_ganancia=[f for f in rentabilidad.filas if f.ganancia is not None][:4],
            avisos=self._avisos(hoy),
        )

    def _avisos(self, hoy: date) -> list[Aviso]:
        avisos = []
        alertas = self.alertas.ejecutar(hoy)
        if alertas:
            primera = alertas[0]
            cuando = "ya venció" if primera.vencido else f"vence en {primera.dias_restantes} días"
            avisos.append(
                Aviso(
                    f"{len(alertas)} lote{'s' if len(alertas) != 1 else ''} por vencer",
                    f"{primera.nombre_producto} {cuando}",
                    "alertas",
                    urgente=True,
                )
            )
        bajos = [
            f
            for f in self.existencias.ejecutar(con_ultima_venta=False)
            if f.estado in (ESTADO_AGOTADO, ESTADO_BAJO_MINIMO) and f.minimo is not None
        ]
        if bajos:
            nombres = ", ".join(f.nombre for f in bajos[:2]) + (
                f" y {len(bajos) - 2} más" if len(bajos) > 2 else ""
            )
            avisos.append(
                Aviso(
                    f"{len(bajos)} producto{'s' if len(bajos) != 1 else ''} bajo el mínimo",
                    nombres,
                    "existencias",
                )
            )
        sin_costo = [
            p
            for p in self.repositorio_productos.listar()
            if p.activo and (p.costo is None or p.costo.neto.monto == 0)
        ]
        if sin_costo:
            plural = "s" if len(sin_costo) != 1 else ""
            avisos.append(
                Aviso(
                    f"{len(sin_costo)} producto{plural} sin costo cargado",
                    "Su margen no se puede calcular",
                    "productos",
                )
            )
        return avisos
