"""Caso de uso: registrar (crear) un producto en el catalogo."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import RepositorioProductos
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero


@dataclass
class RegistrarProducto:
    repositorio: RepositorioProductos

    def ejecutar(
        self,
        codigo: str,
        nombre: str,
        precio: int,
        unidad_venta: UnidadVenta = UnidadVenta.UNIDAD,
        categoria_id: int | None = None,
        costo: int | None = None,
    ) -> Producto:
        if self.repositorio.obtener_por_codigo(codigo) is not None:
            raise DatosProductoInvalidos(f"Ya existe un producto con codigo {codigo}")

        costo_obj = Costo(neto=Dinero(costo), iva=Dinero(0)) if costo is not None else None

        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            precio=Dinero(precio),
            unidad_venta=unidad_venta,
            categoria_id=categoria_id,
            costo=costo_obj,
        )
        self.repositorio.guardar(producto)
        return producto
