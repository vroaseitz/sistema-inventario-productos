"""Casos de uso de F6: rentabilidad por producto (HU-REP-03) y rotacion de productos (HU-REP-04).

Rentabilidad: usa el costo que tenia el producto CUANDO SE VENDIO (queda en la linea de la venta),
no el de hoy, y el costo neto (ADR 0004). Un producto sin costo cargado (o con costo 0) NO se
supone en cero: se informa «sin costo» y su venta queda fuera de la ganancia y del margen, para
no declarar 100 % de ganancia.

Rotacion: productos sin una sola venta en los ultimos N dias, del mas antiguo al mas reciente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from pos.aplicacion.puertos import RepositorioExistencias, RepositorioProductos, RepositorioVentas
from pos.dominio.productos import UnidadVenta


@dataclass(frozen=True)
class FilaRentabilidad:
    codigo: str
    nombre: str
    categoria_id: int | None
    unidades: Decimal | None  # None en granel (se vende por peso)
    venta: int
    costo: int | None  # None = sin costo
    ganancia: int | None
    margen: float | None

    @property
    def sin_costo(self) -> bool:
        return self.costo is None


@dataclass(frozen=True)
class ResumenRentabilidad:
    filas: list[FilaRentabilidad]
    venta_con_costo: int
    ganancia_total: int
    venta_sin_costo: int

    @property
    def margen_total(self) -> float | None:
        return self.ganancia_total / self.venta_con_costo if self.venta_con_costo else None


ORDENES_RENTABILIDAD = ("Mayor ganancia", "Mayor venta", "Mayor margen", "Nombre")


@dataclass
class ReporteRentabilidad:
    repositorio_ventas: RepositorioVentas
    repositorio_productos: RepositorioProductos

    def ejecutar(
        self,
        desde: date,
        hasta: date,
        categoria_id: int | None = None,
        orden: str = "Mayor ganancia",
    ) -> ResumenRentabilidad:
        if hasta < desde:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        acumulado: dict[str, dict] = {}
        for venta in self.repositorio_ventas.por_periodo(desde, hasta):
            for linea in venta.detalles:
                dato = acumulado.setdefault(
                    linea.producto_codigo,
                    {"unidades": Decimal("0"), "venta": 0, "costo": 0, "sin_costo": False},
                )
                dato["unidades"] += linea.cantidad
                dato["venta"] += linea.subtotal.monto
                costo = linea.costo_unitario
                if costo is None or costo.monto == 0:  # C-06: costo 0 = no cargado
                    dato["sin_costo"] = True
                else:
                    dato["costo"] += costo.multiplicado_por(linea.cantidad).monto
        filas = []
        for codigo, dato in acumulado.items():
            producto = self.repositorio_productos.obtener_por_codigo(codigo)
            if categoria_id is not None and (
                producto is None or producto.categoria_id != categoria_id
            ):
                continue
            granel = producto is not None and producto.unidad_venta is UnidadVenta.GRANEL
            if dato["sin_costo"]:
                costo = ganancia = margen = None
            else:
                costo = dato["costo"]
                ganancia = dato["venta"] - costo
                margen = ganancia / dato["venta"] if dato["venta"] else None
            filas.append(
                FilaRentabilidad(
                    codigo,
                    producto.nombre if producto else codigo,
                    producto.categoria_id if producto else None,
                    None if granel else dato["unidades"],
                    dato["venta"],
                    costo,
                    ganancia,
                    margen,
                )
            )
        filas.sort(key=_clave_de(orden))
        con_costo = [f for f in filas if not f.sin_costo]
        return ResumenRentabilidad(
            filas,
            sum(f.venta for f in con_costo),
            sum(f.ganancia for f in con_costo),
            sum(f.venta for f in filas if f.sin_costo),
        )


def _clave_de(orden: str):
    if orden == "Mayor venta":
        return lambda f: -f.venta
    if orden == "Mayor margen":
        return lambda f: (f.margen is None, -(f.margen or 0))
    if orden == "Nombre":
        return lambda f: f.nombre.lower()
    # Mayor ganancia: los «sin costo» al final, no se pueden ordenar por una ganancia que no existe
    return lambda f: (f.ganancia is None, -(f.ganancia or 0))


@dataclass(frozen=True)
class FilaRotacion:
    codigo: str
    nombre: str
    categoria_id: int | None
    activo: bool
    ultima_venta: date | None
    dias_detenido: int | None  # None = nunca se vendio
    existencia: Decimal


@dataclass
class ReporteRotacion:
    repositorio_ventas: RepositorioVentas
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias

    def ejecutar(
        self,
        dias: int = 90,
        categoria_id: int | None = None,
        estado: str = "Activos",
        hoy: date | None = None,
    ) -> list[FilaRotacion]:
        hoy = hoy or date.today()
        corte = hoy - timedelta(days=dias)
        ultimas = self.repositorio_ventas.ultima_venta_por_producto()
        filas = []
        for producto in self.repositorio_productos.listar():
            if estado == "Activos" and not producto.activo:
                continue
            if estado == "Inactivos" and producto.activo:
                continue
            if categoria_id is not None and producto.categoria_id != categoria_id:
                continue
            ultima = ultimas.get(producto.codigo)
            if ultima is not None and ultima > corte:
                continue  # vendio dentro de la ventana: no esta detenido
            existencia = self.repositorio_existencias.obtener(producto.codigo)
            filas.append(
                FilaRotacion(
                    producto.codigo,
                    producto.nombre,
                    producto.categoria_id,
                    producto.activo,
                    ultima,
                    (hoy - ultima).days if ultima else None,
                    existencia.cantidad if existencia else Decimal("0"),
                )
            )
        # Del mas antiguo al mas reciente; los que nunca se vendieron primero.
        filas.sort(key=lambda f: (f.ultima_venta is not None, f.ultima_venta or date.min))
        return filas
