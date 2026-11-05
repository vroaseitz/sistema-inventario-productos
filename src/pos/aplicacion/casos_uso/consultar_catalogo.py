"""Consultas de F2 Catalogo: lista de productos y de categorias (HU-PRD-07, HU-PRD-09, HU-PRD-10).

La busqueda no distingue tildes ni mayusculas y pone primero los productos cuyo nombre (o alguna
de sus palabras) EMPIEZA con lo escrito: «te» muestra «Té verde» antes que «Aceite» (CA-15).
Un producto queda marcado «Revisar» cuando su costo es sospechoso (HU-PRD-09): un costo mayor que
cero pero de menos de $10 casi con certeza es una coma corrida.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pos.aplicacion.puertos import (
    RepositorioCategorias,
    RepositorioExistencias,
    RepositorioProductos,
    RepositorioVentas,
)
from pos.dominio.formato import rango_de_busqueda
from pos.dominio.productos import Producto, UnidadVenta

COSTO_MINIMO_CREIBLE = 10  # CLP: por debajo (y sobre cero) se advierte


def _plano(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sin_tildes.lower()


def motivo_de_revision(producto: Producto) -> str:
    """Por que un producto queda marcado «Revisar»; vacio si esta bien."""
    if producto.costo is not None and 0 < producto.costo.neto.monto < COSTO_MINIMO_CREIBLE:
        neto = producto.costo.neto.monto
        return f"su costo registrado es ${neto}, casi con certeza una coma corrida"
    if producto.precio.monto < COSTO_MINIMO_CREIBLE:
        return f"su precio es ${producto.precio.monto}"
    return ""


def _texto_cantidad(cantidad) -> str:
    """Cantidad sin ceros sobrantes ni notacion cientifica (10, 2.5)."""
    return format(Decimal(str(cantidad)).normalize(), "f")


@dataclass(frozen=True)
class FilaCatalogo:
    codigo: str
    nombre: str
    categoria: str
    precio: int
    granel: bool
    existencia: str
    estado: str  # Activo, Inactivo o Revisar
    sin_costo: bool
    motivo_revision: str = ""


@dataclass
class ConsultarCatalogo:
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias
    repositorio_categorias: RepositorioCategorias

    def ejecutar(
        self,
        buscar: str = "",
        categoria_id: int | None = None,
        estado: str = "Activos",
        costo: str = "Todos",
    ) -> list[FilaCatalogo]:
        termino = _plano(buscar.strip())
        nombres = {c.id: c.nombre for c in self.repositorio_categorias.listar()}
        encontrados = []
        for producto in self.repositorio_productos.listar():
            if estado == "Activos" and not producto.activo:
                continue
            if estado == "Inactivos" and producto.activo:
                continue
            if categoria_id is not None and producto.categoria_id != categoria_id:
                continue
            sin_costo = producto.costo is None or producto.costo.neto.monto == 0
            if costo == "Sin costo" and not sin_costo:
                continue
            if costo == "Con costo" and sin_costo:
                continue
            nombre_plano = _plano(producto.nombre)
            if termino and termino not in nombre_plano and termino not in _plano(producto.codigo):
                continue
            rango = rango_de_busqueda(producto.nombre, buscar)  # CA-15
            motivo = motivo_de_revision(producto)
            existencia = self.repositorio_existencias.obtener(producto.codigo)
            granel = producto.unidad_venta is UnidadVenta.GRANEL
            encontrados.append(
                (
                    rango,
                    nombre_plano,
                    FilaCatalogo(
                        producto.codigo,
                        producto.nombre,
                        nombres.get(producto.categoria_id, "Sin categoría"),
                        producto.precio.monto,
                        granel,
                        "granel"
                        if granel
                        else _texto_cantidad(existencia.cantidad if existencia else 0),
                        "Inactivo" if not producto.activo else ("Revisar" if motivo else "Activo"),
                        sin_costo,
                        motivo,
                    ),
                )
            )
        encontrados.sort(key=lambda t: (t[0], t[1]))
        return [fila for _, _, fila in encontrados]


@dataclass(frozen=True)
class FilaCategoria:
    id: int
    nombre: str
    activa: bool
    productos: int
    venta_mes: int
    participacion: float


@dataclass
class ConsultarCategorias:
    repositorio_categorias: RepositorioCategorias
    repositorio_productos: RepositorioProductos
    repositorio_ventas: RepositorioVentas

    def ejecutar(self, hoy: date | None = None) -> list[FilaCategoria]:
        hoy = hoy or date.today()
        productos = self.repositorio_categorias.contar_productos()
        por_codigo = {p.codigo: p.categoria_id for p in self.repositorio_productos.listar()}
        venta: dict[int, int] = {}
        for v in self.repositorio_ventas.por_periodo(hoy.replace(day=1), hoy):
            for linea in v.detalles:
                categoria = por_codigo.get(linea.producto_codigo)
                if categoria is not None:
                    venta[categoria] = venta.get(categoria, 0) + linea.subtotal.monto
        total = sum(venta.values())
        filas = [
            FilaCategoria(
                c.id,
                c.nombre,
                c.activa,
                productos.get(c.id, 0),
                venta.get(c.id, 0),
                venta.get(c.id, 0) / total if total else 0.0,
            )
            for c in self.repositorio_categorias.listar()
        ]
        return sorted(filas, key=lambda f: (-f.venta_mes, -f.productos, f.nombre.lower()))
