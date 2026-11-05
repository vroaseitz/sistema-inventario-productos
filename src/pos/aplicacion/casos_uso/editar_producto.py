"""Caso de uso: editar un producto existente y registrar cambios de precio."""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioCategorias,
    RepositorioHistorial,
    RepositorioProductos,
)
from pos.aplicacion.sincronizacion import encolar_producto, encolar_producto_codigo
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.formato import formatear_clp
from pos.dominio.productos import RegistroCambioPrecio
from pos.dominio.value_objects import Costo, Dinero


@dataclass
class EditarProducto:
    repositorio_productos: RepositorioProductos
    repositorio_historial: RepositorioHistorial
    cola: ColaSincronizacion | None = None
    repositorio_categorias: RepositorioCategorias | None = None
    auditor: Auditor | None = None

    def cambiar_codigo(self, anterior: str, nuevo: str) -> str:
        """Cambia el codigo de barras (CA-19). No puede repetirse; queda en la auditoria.

        Devuelve el codigo final (sin espacios sobrantes). Si es el mismo, no hace nada.
        """
        nuevo = nuevo.strip()
        if not nuevo:
            raise DatosProductoInvalidos("El código de barras no puede quedar vacío")
        if nuevo == anterior:
            return anterior
        producto = self.repositorio_productos.obtener_por_codigo(anterior)
        if producto is None:
            raise DatosProductoInvalidos(f"El producto con código {anterior} no existe.")
        if self.repositorio_productos.obtener_por_codigo(nuevo) is not None:
            raise DatosProductoInvalidos(f"Ya existe un producto con código {nuevo}")
        self.repositorio_productos.cambiar_codigo(anterior, nuevo)
        encolar_producto_codigo(self.cola, anterior, nuevo)
        if self.auditor is not None:
            self.auditor.registrar(
                "Cambio de código de barras", f"{producto.nombre} ({nuevo})", anterior, nuevo
            )
        return nuevo

    def ejecutar(
        self,
        codigo: str,
        nuevo_nombre: str,
        nuevo_precio: int,
        nueva_categoria_id: int | None,
        usuario: str,
        costo: int | None = None,
        perecible: bool = False,
        dias_aviso: int | None = None,
        motivo_precio: str = "",
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
        producto.perecible = perecible
        producto.dias_aviso = dias_aviso

        # 3. Guardar PRIMERO el producto
        self.repositorio_productos.guardar(producto)
        # Antes un cambio de precio o categoria quedaba solo en la base local.
        nombre_categoria = (
            self.repositorio_categorias.nombre_de(nueva_categoria_id)
            if self.repositorio_categorias
            else None
        )
        encolar_producto(self.cola, producto, nombre_categoria)

        # 4. SOLO DESPUÉS (si no hay error y si el precio cambió), registrar en historial
        if hubo_cambio_precio:
            registro = RegistroCambioPrecio(
                codigo_producto=codigo,
                precio_anterior=precio_anterior,
                precio_nuevo=nuevo_precio_dinero,
                usuario=usuario,
                motivo=motivo_precio.strip(),
            )
            self.repositorio_historial.guardar_registro_precio(registro)
            if self.auditor is not None:
                self.auditor.registrar(
                    "Cambio de precio",
                    f"{producto.nombre} ({codigo})",
                    formatear_clp(precio_anterior.monto),
                    formatear_clp(nuevo_precio),
                )
