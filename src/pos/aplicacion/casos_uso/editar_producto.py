"""Caso de uso: editar un producto existente y registrar cambios de precio."""

from __future__ import annotations
from dataclasses import dataclass

from pos.aplicacion.puertos import RepositorioProductos, RepositorioHistorial
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import RegistroCambioPrecio
from pos.dominio.value_objects import Dinero


@dataclass
class EditarProducto:
    repositorio_productos: RepositorioProductos
    repositorio_historial: RepositorioHistorial

    def ejecutar(
        self,
        codigo: str,
        nuevo_nombre: str,
        nuevo_precio: int,
        nueva_categoria_id: str,
        usuario: str,
    ) -> None:
        
        # 1. Obtener el producto actual
        producto = self.repositorio_productos.obtener_por_codigo(codigo)
        if not producto:
            raise DatosProductoInvalidos(f"El producto con código {codigo} no existe.")

        nuevo_precio_dinero = Dinero(nuevo_precio)

        # 2. Validación central de HU-PRD-05: Evaluar si el precio cambió
        if producto.precio != nuevo_precio_dinero:
            registro = RegistroCambioPrecio(
                codigo_producto=codigo,
                precio_anterior=producto.precio,
                precio_nuevo=nuevo_precio_dinero,
                usuario=usuario
            )
            self.repositorio_historial.guardar_registro_precio(registro)

        # 3. Actualizar la entidad con los nuevos valores
        producto.nombre = nuevo_nombre.strip().upper()
        producto.precio = nuevo_precio_dinero
        producto.categoria_id = nueva_categoria_id

        # 4. Guardar los cambios en el catálogo
        self.repositorio_productos.guardar(producto)