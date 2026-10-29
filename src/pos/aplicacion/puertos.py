"""Puertos (interfaces) de la capa de aplicacion.

Los casos de uso dependen de estas abstracciones, no de implementaciones concretas
(Principio de Inversion de Dependencias). La infraestructura (SQLite, Supabase) las
implementa. Se usa typing.Protocol para no obligar a heredar.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pos.dominio.caja import MovimientoCaja, TurnoCaja
from pos.dominio.inventario import AjusteInventario, Existencia
from pos.dominio.lotes import Lote
from pos.dominio.productos import Producto, RegistroCambioPrecio
from pos.dominio.ventas import Venta


@runtime_checkable
class RepositorioProductos(Protocol):
    def guardar(self, producto: Producto) -> None: ...
    def obtener_por_codigo(self, codigo: str) -> Producto | None: ...
    def listar(self) -> list[Producto]: ...
    def buscar(self, termino: str) -> list[Producto]: ...


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
class RepositorioTurnosCaja(Protocol):
    """Puerto para persistir el turno de caja y sus movimientos (HU-CAJ-01/04)."""

    def guardar(self, turno: TurnoCaja) -> None: ...
    def obtener_abierto(self) -> TurnoCaja | None: ...
    def registrar_movimiento(self, turno_id: int, movimiento: MovimientoCaja) -> None: ...


@runtime_checkable
class RepositorioVentas(Protocol):
    """Puerto para persistir la venta, sus lineas y sus pagos (HU-VTA-01/03/04)."""

    def guardar(self, venta: Venta) -> None: ...
    def obtener_por_turno(self, turno_caja_id: int) -> list[Venta]: ...


@runtime_checkable
class PublicadorRemoto(Protocol):
    """Publica una operacion en el destino remoto (Supabase/PostgreSQL).

    Debe ser idempotente respecto de `id_cliente`: publicar dos veces la misma
    operacion no puede duplicar datos en el destino.
    """

    def publicar(self, operacion: dict) -> None: ...


@runtime_checkable
class RepositorioHistorial(Protocol):
    """Puerto para persistir el historial de cambios de precio (HU-PRD-05)."""

    def guardar_registro_precio(self, registro: RegistroCambioPrecio) -> None: ...


@runtime_checkable
class RepositorioAjustes(Protocol):
    """Puerto para persistir el historial de ajustes (HU mermas y ajustes)."""

    def guardar_ajuste(self, ajuste: AjusteInventario) -> None: ...


@runtime_checkable
class RepositorioLotes(Protocol):
    """Puerto de lotes con vencimiento (HU-INV-02)."""

    def guardar(self, lote: Lote) -> None: ...
    def por_producto(self, codigo_producto: str) -> list[Lote]: ...
    def con_saldo(self) -> list[Lote]: ...
