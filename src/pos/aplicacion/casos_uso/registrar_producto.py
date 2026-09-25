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
        categoria_id: str,
        unidad_venta: UnidadVenta = UnidadVenta.UNIDAD,
        es_perecible: bool = False,
        dias_aviso_vencimiento: int | None = None,
    ) -> Producto:
        
        producto_existente = self.repositorio.obtener_por_codigo(codigo)
        if producto_existente and producto_existente.activo:
            raise DatosProductoInvalidos(f"Ya existe un producto activo con codigo {codigo}")
            
        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            precio=Dinero(precio),
            categoria_id=categoria_id,
            unidad_venta=unidad_venta,
            es_perecible=es_perecible,
            dias_aviso_vencimiento=dias_aviso_vencimiento,
        )
        self.repositorio.guardar(producto)
        return producto