"""Caso de uso: desactivar o reactivar un producto (HU-PRD-06).

Desactivar saca el producto de la venta y de las listas sin borrar su historial. Se sincroniza y
deja rastro en la auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.puertos import ColaSincronizacion, RepositorioCategorias, RepositorioProductos
from pos.aplicacion.sincronizacion import encolar_producto
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto


@dataclass
class CambiarEstadoProducto:
    repositorio: RepositorioProductos
    cola: ColaSincronizacion | None = None
    repositorio_categorias: RepositorioCategorias | None = None
    auditor: Auditor | None = None

    def ejecutar(self, codigo: str, activo: bool) -> Producto:
        producto = self.repositorio.obtener_por_codigo(codigo)
        if producto is None:
            raise DatosProductoInvalidos(f"No existe un producto con codigo {codigo}")
        if producto.activo == activo:
            return producto
        producto.activo = activo
        self.repositorio.guardar(producto)
        categoria = (
            self.repositorio_categorias.nombre_de(producto.categoria_id)
            if self.repositorio_categorias
            else None
        )
        encolar_producto(self.cola, producto, categoria)
        if self.auditor is not None:
            self.auditor.registrar(
                "Desactivación de producto" if not activo else "Reactivación de producto",
                f"{producto.nombre} ({codigo})",
                "Activo" if not activo else "Inactivo",
                "Inactivo" if not activo else "Activo",
            )
        return producto
