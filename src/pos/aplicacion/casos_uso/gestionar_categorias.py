"""Categorias del catalogo: crear, renombrar, fusionar y desactivar (CA-16, HU-PRD-10).

Renombrar cambia solo la etiqueta: los productos siguen siendo los mismos y el historial de ventas
queda intacto. Si el nombre nuevo ya existe se rechaza y se propone fusionar. Fusionar pasa todos
los productos de una categoria a otra y borra la de origen; no se puede deshacer y queda en la
auditoria con quien la hizo y cuantos productos movio. Desactivar la saca del selector sin tocar los
productos que ya la usan (una categoria con productos nunca se borra a la fuerza).
"""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.puertos import ColaSincronizacion, RepositorioCategorias, RepositorioProductos
from pos.aplicacion.sincronizacion import (
    encolar_categoria,
    encolar_categoria_eliminada,
    encolar_categoria_renombrada,
    encolar_producto,
)
from pos.dominio.categorias import Categoria, clave_de_nombre, normalizar_nombre_categoria
from pos.dominio.errores import DatosProductoInvalidos


@dataclass
class GestionarCategorias:
    repositorio: RepositorioCategorias
    repositorio_productos: RepositorioProductos
    cola: ColaSincronizacion | None = None
    auditor: Auditor | None = None

    def crear(self, nombre: str) -> Categoria:
        categoria, creada = self.repositorio.agregar(nombre)
        if not creada:
            raise DatosProductoInvalidos(f"Ya existe una categoría llamada {categoria.nombre}")
        encolar_categoria(self.cola, categoria.nombre, categoria.activa)
        self._auditar("Nueva categoría", categoria.nombre, "—", "creada")
        return categoria

    def renombrar(self, categoria_id: int, nombre_nuevo: str) -> Categoria:
        categoria = self._obtener(categoria_id)
        nombre = normalizar_nombre_categoria(nombre_nuevo)
        for otra in self.repositorio.listar():
            if otra.id != categoria_id and clave_de_nombre(otra.nombre) == clave_de_nombre(nombre):
                raise DatosProductoInvalidos(
                    f"Ya existe una categoría llamada {otra.nombre}: usa «Fusionar categorías»"
                )
        if nombre == categoria.nombre:
            return categoria
        self.repositorio.renombrar(categoria_id, nombre)
        encolar_categoria_renombrada(self.cola, categoria.nombre, nombre)
        self._reenviar_productos(categoria_id, nombre)
        self._auditar("Renombrar categoría", nombre, categoria.nombre, nombre)
        return self._obtener(categoria_id)

    def fusionar(self, origen_id: int, destino_id: int) -> int:
        """Mueve los productos de `origen` a `destino`, borra `origen` y dice cuantos movio."""
        if origen_id == destino_id:
            raise DatosProductoInvalidos("La categoría de origen y la de destino son la misma")
        origen = self._obtener(origen_id)
        destino = self._obtener(destino_id)
        if not destino.activa:
            raise DatosProductoInvalidos(
                f"«{destino.nombre}» está desactivada: actívala antes de fusionar hacia ella"
            )
        movidos = 0
        for producto in self.repositorio_productos.listar():
            if producto.categoria_id == origen_id:
                producto.categoria_id = destino_id
                self.repositorio_productos.guardar(producto)
                encolar_producto(self.cola, producto, destino.nombre)
                movidos += 1
        self.repositorio.eliminar(origen_id)
        encolar_categoria_eliminada(self.cola, origen.nombre)
        self._auditar(
            "Fusión de categorías",
            f"{origen.nombre} → {destino.nombre}",
            f"{movidos} productos",
            "fusionadas",
            {"productos_movidos": movidos},
        )
        return movidos

    def cambiar_estado(self, categoria_id: int, activa: bool) -> Categoria:
        categoria = self._obtener(categoria_id)
        if categoria.activa == activa:
            return categoria
        self.repositorio.cambiar_estado(categoria_id, activa)
        encolar_categoria(self.cola, categoria.nombre, activa)
        self._auditar(
            "Reactivación de categoría" if activa else "Desactivación de categoría",
            categoria.nombre,
            "Inactiva" if activa else "Activa",
            "Activa" if activa else "Inactiva",
        )
        return self._obtener(categoria_id)

    # ------------------------------------------------------------------ privados --

    def _obtener(self, categoria_id: int) -> Categoria:
        categoria = self.repositorio.obtener(categoria_id)
        if categoria is None:
            raise DatosProductoInvalidos("La categoría no existe")
        return categoria

    def _reenviar_productos(self, categoria_id: int, nombre: str) -> None:
        """El nombre es lo que viaja a Supabase: los productos se vuelven a enviar con el nuevo."""
        for producto in self.repositorio_productos.listar():
            if producto.categoria_id == categoria_id:
                encolar_producto(self.cola, producto, nombre)

    def _auditar(
        self, accion: str, registro: str, antes: str, despues: str, detalle: dict | None = None
    ) -> None:
        if self.auditor is not None:
            self.auditor.registrar(accion, registro, antes, despues, detalle)
