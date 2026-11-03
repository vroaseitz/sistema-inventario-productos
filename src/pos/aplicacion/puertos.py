"""Puertos (interfaces) de la capa de aplicacion.

Los casos de uso dependen de estas abstracciones, no de implementaciones concretas
(Principio de Inversion de Dependencias). La infraestructura (SQLite, Supabase) las
implementa. Se usa typing.Protocol para no obligar a heredar.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from pos.dominio.caja import MovimientoCaja, TurnoCaja
from pos.dominio.categorias import Categoria
from pos.dominio.clientes import Cliente, MovimientoCliente
from pos.dominio.compras import FacturaCompra
from pos.dominio.inventario import AjusteInventario, Existencia
from pos.dominio.lotes import Lote
from pos.dominio.productos import Producto, RegistroCambioPrecio
from pos.dominio.usuarios import Usuario
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
    def por_periodo(self, desde: date, hasta: date) -> list[Venta]: ...


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


@runtime_checkable
class RepositorioUsuarios(Protocol):
    """Puerto de usuarios para el acceso local (HU-USR-01)."""

    def guardar(self, usuario: Usuario) -> None: ...
    def obtener_por_nombre(self, nombre: str) -> Usuario | None: ...
    def hay_usuarios(self) -> bool: ...
    def listar(self) -> list[Usuario]: ...
    def registrar_acceso(self, usuario_id: int) -> None: ...


@runtime_checkable
class RepositorioTicketsEspera(Protocol):
    """Puerto para conservar los tickets sin cobrar al cerrar la ventana (O-25)."""

    def guardar(self, tickets: list[dict]) -> None: ...
    def cargar(self) -> list[dict]: ...


@runtime_checkable
class RepositorioClientes(Protocol):
    """Puerto de clientes con credito y sus movimientos (HU-CLI-01 a 05)."""

    def guardar(self, cliente: Cliente) -> None: ...
    def obtener(self, cliente_id: int) -> Cliente | None: ...
    def listar(self) -> list[Cliente]: ...
    def agregar_movimiento(self, movimiento: MovimientoCliente) -> None: ...
    def movimientos(self, cliente_id: int) -> list[MovimientoCliente]: ...
    def abonos_en_efectivo_del_turno(self, turno_caja_id: int) -> int: ...


@runtime_checkable
class RepositorioFacturasCompra(Protocol):
    """Puerto de facturas de compra a proveedor (HU-CMP-01/02)."""

    def guardar(self, factura: FacturaCompra) -> None: ...
    def listar(
        self, desde: date | None = None, hasta: date | None = None
    ) -> list[FacturaCompra]: ...
    def proveedores(self) -> list[str]: ...


@runtime_checkable
class RepositorioAuditoria(Protocol):
    """Puerto del registro de auditoria (HU-USR-03): quien hizo que y cuando."""

    def registrar(
        self,
        usuario: str,
        accion: str,
        detalle: dict,
        registro: str = "",
        antes: str = "",
        despues: str = "",
    ) -> None: ...
    def listar(
        self,
        accion: str | None = None,
        usuario: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[dict]: ...


@runtime_checkable
class RepositorioConfiguracion(Protocol):
    """Puerto de los parametros de operacion (F7 Configuracion)."""

    def obtener(self, clave: str) -> int: ...
    def guardar(self, clave: str, valor: int) -> None: ...
    def restaurar_valores_por_defecto(self) -> None: ...


@runtime_checkable
class RepositorioCategorias(Protocol):
    """Puerto de categorias de producto (C-02, HU-PRD-10)."""

    def listar(self) -> list[Categoria]: ...
    def nombre_de(self, categoria_id: int | None) -> str | None: ...
    def agregar(self, nombre: str) -> tuple[Categoria, bool]: ...
    def sembrar(self, nombres: list[str] | tuple[str, ...]) -> int: ...
