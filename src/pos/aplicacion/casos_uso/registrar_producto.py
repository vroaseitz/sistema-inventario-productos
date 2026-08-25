"""Caso de uso: registrar (crear) un producto en el catalogo."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import RepositorioProductos
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Dinero


@dataclass
class RegistrarProducto:
    repositorio: RepositorioProductos

    def ejecutar(
        self,
        codigo: str,
        nombre: str,
        precio: int,
        unidad_venta: UnidadVenta = UnidadVenta.UNIDAD,
        categoria: str | None = None,
    ) -> Producto:
        if self.repositorio.obtener_por_codigo(codigo) is not None:
            raise DatosProductoInvalidos(f"Ya existe un producto con codigo {codigo}")
        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            precio=Dinero(precio),
            unidad_venta=unidad_venta,
            categoria=categoria,
        )
        self.repositorio.guardar(producto)
        return producto
