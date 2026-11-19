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
from pos.dominio.productos import TASAS_IABA, RegistroCambioPrecio
from pos.dominio.value_objects import Dinero


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
        desc_dias_1: int | None = None,
        desc_pct_1: int | None = None,
        desc_dias_2: int | None = None,
        desc_pct_2: int | None = None,
        iaba_pct: int | None = None,
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
        producto.iaba_pct = iaba_pct
        if costo is not None:
            producto.fijar_costo_neto(costo)
        elif producto.costo is not None:
            producto.fijar_costo_neto(producto.costo.neto.monto)  # CA-21: re-calcula el IABA
        producto.perecible = perecible
        producto.dias_aviso = dias_aviso
        # O-42: vacio = vuelve a la politica por defecto. Se valida antes de guardar nada.
        producto.desc_dias_1, producto.desc_pct_1 = desc_dias_1, desc_pct_1
        producto.desc_dias_2, producto.desc_pct_2 = desc_dias_2, desc_pct_2
        producto.politica_descuento()
        if iaba_pct is not None and iaba_pct not in TASAS_IABA:
            raise DatosProductoInvalidos("El impuesto adicional a bebidas es de 10 % o 18 %")

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
