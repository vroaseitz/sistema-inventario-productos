"""Caso de uso: editar un producto existente y registrar cambios de precio."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import RepositorioHistorial, RepositorioProductos
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.productos import RegistroCambioPrecio
from pos.dominio.value_objects import Costo, Dinero


@dataclass
class EditarProducto:
    repositorio_productos: RepositorioProductos
    repositorio_historial: RepositorioHistorial

    def ejecutar(
        self,
        codigo: str,
        nuevo_nombre: str,
        nuevo_precio: int,
        nueva_categoria_id: int | None,
        usuario: str,
        costo: int | None = None,
    ) -> None:
        # 1. Obtener el producto actual
        producto = self.repositorio_productos.obtener_por_codigo(codigo)
        if not producto:
            raise DatosProductoInvalidos(f"El producto con código {codigo} no existe.")

        precio_anterior = producto.precio
        nuevo_precio_dinero = Dinero(nuevo_precio)
        hubo_cambio_precio = precio_anterior != nuevo_precio_dinero

        # 2. Actualizar la entidad con los nuevos valores (sin forzar .upper())
        producto.nombre = nuevo_nombre.strip()
        producto.precio = nuevo_precio_dinero
        producto.categoria_id = nueva_categoria_id
        if costo is not None:
            producto.costo = Costo(neto=Dinero(costo), iva=Dinero(0))

        # 3. Guardar PRIMERO el producto
        self.repositorio_productos.guardar(producto)

        # 4. SOLO DESPUÉS (si no hay error y si el precio cambió), registrar en historial
        if hubo_cambio_precio:
            registro = RegistroCambioPrecio(
                codigo_producto=codigo,
                precio_anterior=precio_anterior,
                precio_nuevo=nuevo_precio_dinero,
                usuario=usuario,
            )
            self.repositorio_historial.guardar_registro_precio(registro)
