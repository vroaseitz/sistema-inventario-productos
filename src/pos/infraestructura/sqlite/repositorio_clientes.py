"""Repositorio de clientes con credito sobre SQLite. Implementa RepositorioClientes."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from pos.dominio.clientes import (
    Cliente,
    LineaConsumo,
    MovimientoCliente,
    TipoMovimientoCliente,
)
from pos.dominio.value_objects import Dinero


class RepositorioClientesSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, cliente: Cliente) -> None:
        """Crea el cliente o actualiza sus datos (nunca se borra: se desactiva)."""
        if cliente.id is None:
            cursor = self._con.execute(
                "INSERT INTO clientes (nombre, telefono, correo, observaciones, activo) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    cliente.nombre,
                    cliente.telefono,
                    cliente.correo,
                    cliente.observaciones,
                    int(cliente.activo),
                ),
            )
            cliente.id = cursor.lastrowid
        else:
            self._con.execute(
                "UPDATE clientes SET nombre = ?, telefono = ?, correo = ?, observaciones = ?, "
                "activo = ? WHERE id = ?",
                (
                    cliente.nombre,
                    cliente.telefono,
                    cliente.correo,
                    cliente.observaciones,
                    int(cliente.activo),
                    cliente.id,
                ),
            )
        self._con.commit()

    def obtener(self, cliente_id: int) -> Cliente | None:
        fila = self._con.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
        return self._a_cliente(fila) if fila else None

    def listar(self) -> list[Cliente]:
        filas = self._con.execute("SELECT * FROM clientes ORDER BY id").fetchall()
        return [self._a_cliente(f) for f in filas]

    def agregar_movimiento(self, movimiento: MovimientoCliente) -> None:
        cursor = self._con.execute(
            "INSERT INTO movimientos_cliente (uuid, cliente_id, tipo, monto, fecha, detalle, "
            "medio, venta_uuid, turno_caja_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                movimiento.uuid,
                movimiento.cliente_id,
                movimiento.tipo.value,
                movimiento.monto,
                movimiento.fecha.isoformat(),
                movimiento.detalle,
                movimiento.medio,
                movimiento.venta_uuid,
                movimiento.turno_caja_id,
            ),
        )
        movimiento.id = cursor.lastrowid
        self._con.commit()

    def movimientos(self, cliente_id: int) -> list[MovimientoCliente]:
        filas = self._con.execute(
            "SELECT * FROM movimientos_cliente WHERE cliente_id = ? ORDER BY fecha, id",
            (cliente_id,),
        ).fetchall()
        return [self._a_movimiento(f) for f in filas]

    def abonos_en_efectivo_del_turno(self, turno_caja_id: int) -> int:
        fila = self._con.execute(
            "SELECT COALESCE(SUM(monto), 0) AS total FROM movimientos_cliente "
            "WHERE tipo = 'abono' AND medio = 'efectivo' AND turno_caja_id = ?",
            (turno_caja_id,),
        ).fetchone()
        return int(fila["total"])

    def lineas_de_consumo(self, venta_uuid: str) -> list[LineaConsumo]:
        """Productos de una venta a credito: nombre, cantidad y lo cobrado por cada linea."""
        filas = self._con.execute(
            "SELECT COALESCE(p.nombre, d.producto_codigo) AS nombre, d.cantidad, "
            "d.precio_unitario, d.descuento_linea "
            "FROM ventas v JOIN venta_detalles d ON d.venta_id = v.id "
            "LEFT JOIN productos p ON p.codigo = d.producto_codigo "
            "WHERE v.uuid = ? ORDER BY d.id",
            (venta_uuid,),
        ).fetchall()
        lineas = []
        for f in filas:
            cantidad = Decimal(f["cantidad"])
            bruto = Dinero(f["precio_unitario"]).multiplicado_por(cantidad).monto
            lineas.append(LineaConsumo(f["nombre"], cantidad, bruto - f["descuento_linea"]))
        return lineas

    @staticmethod
    def _a_cliente(fila: sqlite3.Row) -> Cliente:
        return Cliente(
            nombre=fila["nombre"],
            telefono=fila["telefono"],
            correo=fila["correo"],
            observaciones=fila["observaciones"],
            activo=bool(fila["activo"]),
            id=fila["id"],
        )

    @staticmethod
    def _a_movimiento(fila: sqlite3.Row) -> MovimientoCliente:
        return MovimientoCliente(
            cliente_id=fila["cliente_id"],
            tipo=TipoMovimientoCliente(fila["tipo"]),
            monto=fila["monto"],
            fecha=date.fromisoformat(fila["fecha"]),
            detalle=fila["detalle"],
            medio=fila["medio"],
            venta_uuid=fila["venta_uuid"],
            turno_caja_id=fila["turno_caja_id"],
            uuid=fila["uuid"],
            id=fila["id"],
        )
