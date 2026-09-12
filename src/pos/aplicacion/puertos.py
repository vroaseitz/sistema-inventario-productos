"""Puertos (interfaces) de la capa de aplicacion.

Los casos de uso dependen de estas abstracciones, no de implementaciones concretas
(Principio de Inversion de Dependencias). La infraestructura (SQLite, Supabase) las
implementa. Se usa typing.Protocol para no obligar a heredar.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pos.dominio.inventario import Existencia
from pos.dominio.productos import Producto


@runtime_checkable
class RepositorioProductos(Protocol):
    def guardar(self, producto: Producto) -> None: ...
    def obtener_por_codigo(self, codigo: str) -> Producto | None: ...
    def listar(self) -> list[Producto]: ...


@runtime_checkable
class RepositorioExistencias(Protocol):
    def obtener(self, codigo_producto: str) -> Existencia | None: ...
    def guardar(self, existencia: Existencia) -> None: ...


@runtime_checkable
class ColaSincronizacion(Protocol):
    """Cola de operaciones pendientes de sincronizar con Supabase (modo offline)."""

    def encolar(self, entidad: str, operacion: str, datos: dict, id_cliente: str) -> None: ...
    def pendientes(self) -> list[dict]: ...
    def marcar_sincronizada(self, id_cliente: str) -> None: ...


@runtime_checkable
class PublicadorRemoto(Protocol):
    """Publica una operacion en el destino remoto (Supabase/PostgreSQL).

    Debe ser idempotente respecto de `id_cliente`: publicar dos veces la misma
    operacion no puede duplicar datos en el destino.
    """

    def publicar(self, operacion: dict) -> None: ...
