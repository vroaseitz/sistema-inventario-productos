"""Casos de uso de clientes con credito (HU-CLI-01) y abonos (HU-CLI-03)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date

from pos.aplicacion.puertos import RepositorioClientes, RepositorioTurnosCaja
from pos.dominio.clientes import (
    MEDIOS_ABONO,
    Cliente,
    MovimientoCliente,
    TipoMovimientoCliente,
    saldo_de,
)
from pos.dominio.errores import ReglaClienteInvalida
from pos.dominio.formato import formatear_clp


def _clave(nombre: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.lower().split())


@dataclass
class GestionarClientes:
    repositorio: RepositorioClientes

    def crear(
        self, nombre: str, telefono: str = "", correo: str = "", observaciones: str = ""
    ) -> Cliente:
        cliente = Cliente(nombre, telefono, correo, observaciones)  # valida nombre y contacto
        self._validar_nombre_unico(cliente)
        self.repositorio.guardar(cliente)
        return cliente

    def modificar(
        self,
        cliente_id: int,
        nombre: str,
        telefono: str = "",
        correo: str = "",
        observaciones: str = "",
    ) -> Cliente:
        actual = self._obtener(cliente_id)
        cliente = Cliente(nombre, telefono, correo, observaciones, actual.activo, actual.id)
        self._validar_nombre_unico(cliente)
        self.repositorio.guardar(cliente)
        return cliente

    def cambiar_estado(self, cliente_id: int, activo: bool) -> Cliente:
        """Desactivar saca al cliente de la lista de cobro; su historial queda intacto."""
        cliente = self._obtener(cliente_id)
        cliente.activo = activo
        self.repositorio.guardar(cliente)
        return cliente

    def _obtener(self, cliente_id: int) -> Cliente:
        cliente = self.repositorio.obtener(cliente_id)
        if cliente is None:
            raise ReglaClienteInvalida("El cliente no existe")
        return cliente

    def _validar_nombre_unico(self, cliente: Cliente) -> None:
        for otro in self.repositorio.listar():
            if otro.id != cliente.id and _clave(otro.nombre) == _clave(cliente.nombre):
                raise ReglaClienteInvalida(f"Ya existe un cliente llamado {otro.nombre}")


@dataclass
class RegistrarAbono:
    """Un abono baja el saldo del cliente. En efectivo entra a la gaveta de la jornada abierta."""

    repositorio_clientes: RepositorioClientes
    repositorio_turnos: RepositorioTurnosCaja

    def ejecutar(
        self,
        cliente_id: int,
        monto: int,
        medio: str,
        fecha: date | None = None,
        detalle: str = "",
    ) -> MovimientoCliente:
        cliente = self.repositorio_clientes.obtener(cliente_id)
        if cliente is None:
            raise ReglaClienteInvalida("El cliente no existe")
        if medio not in MEDIOS_ABONO:
            raise ReglaClienteInvalida("Elige el medio de pago del abono")
        if monto <= 0:
            raise ReglaClienteInvalida("El monto del abono debe ser mayor que cero")
        saldo = saldo_de(self.repositorio_clientes.movimientos(cliente_id))
        if monto > saldo:
            raise ReglaClienteInvalida(
                f"El abono ({formatear_clp(monto)}) supera el saldo de "
                f"{cliente.nombre} ({formatear_clp(saldo)})"
            )
        turno_id = None
        if medio == "efectivo":
            turno = self.repositorio_turnos.obtener_abierto()
            if turno is None:
                raise ReglaClienteInvalida(
                    "Abre la jornada de caja para recibir un abono en efectivo"
                )
            turno_id = turno.id
        movimiento = MovimientoCliente(
            cliente_id=cliente_id,
            tipo=TipoMovimientoCliente.ABONO,
            monto=monto,
            fecha=fecha or date.today(),
            detalle=detalle or f"Abono en {medio}",
            medio=medio,
            turno_caja_id=turno_id,
        )
        self.repositorio_clientes.agregar_movimiento(movimiento)
        return movimiento
