"""Caso de uso: registrar (crear) un producto en el catalogo."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import ColaSincronizacion, RepositorioCategorias, RepositorioProductos
from pos.aplicacion.sincronizacion import encolar_producto
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero


@dataclass
class RegistrarProducto:
    repositorio: RepositorioProductos
    cola: ColaSincronizacion | None = None
    repositorio_categorias: RepositorioCategorias | None = None

    def ejecutar(
        self,
        codigo: str,
        nombre: str,
        precio: int,
        unidad_venta: UnidadVenta = UnidadVenta.UNIDAD,
        categoria_id: int | None = None,
        costo: int | None = None,
        perecible: bool = False,
        dias_aviso: int | None = None,
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
            perecible=perecible,
            dias_aviso=dias_aviso,
        )
        self.repositorio.guardar(producto)
        nombre_categoria = (
            self.repositorio_categorias.nombre_de(categoria_id)
            if self.repositorio_categorias
            else None
        )
        encolar_producto(self.cola, producto, nombre_categoria)
        return producto
