"""Repositorio de facturas de compra sobre SQLite. Implementa RepositorioFacturasCompra."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from pos.dominio.compras import EstadoFactura, FacturaCompra, LineaFactura


class RepositorioFacturasCompraSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, factura: FacturaCompra) -> None:
        cursor = self._con.execute(
            "INSERT INTO facturas_compra (proveedor, numero, fecha, neto, impuestos, estado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                factura.proveedor,
                factura.numero,
                factura.fecha.isoformat(),
                factura.neto,
                factura.impuestos,
                factura.estado.value,
            ),
        )
        factura.id = cursor.lastrowid
        for linea in factura.lineas:
            self._con.execute(
                "INSERT INTO facturas_compra_lineas (factura_id, codigo_producto, cantidad, "
                "costo_unitario_neto, costo_anterior, fecha_vencimiento, codigo_lote) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    factura.id,
                    linea.codigo_producto,
                    str(linea.cantidad),
                    linea.costo_unitario_neto,
                    linea.costo_anterior,
                    linea.fecha_vencimiento.isoformat() if linea.fecha_vencimiento else None,
                    linea.codigo_lote,
                ),
            )
        self._con.commit()

    def existe(self, proveedor: str, numero: str) -> bool:
        fila = self._con.execute(
            "SELECT 1 FROM facturas_compra WHERE proveedor = ? AND numero = ?",
            (proveedor, numero),
        ).fetchone()
        return fila is not None

    def listar(self, desde: date | None = None, hasta: date | None = None) -> list[FacturaCompra]:
        consulta = "SELECT * FROM facturas_compra"
        condiciones, parametros = [], []
        if desde is not None:
            condiciones.append("fecha >= ?")
            parametros.append(desde.isoformat())
        if hasta is not None:
            condiciones.append("fecha <= ?")
            parametros.append(hasta.isoformat())
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        filas = self._con.execute(consulta + " ORDER BY fecha DESC, id DESC", parametros)
        return [self._a_factura(f) for f in filas.fetchall()]

    def proveedores(self) -> list[str]:
        filas = self._con.execute(
            "SELECT DISTINCT proveedor FROM facturas_compra ORDER BY proveedor COLLATE NOCASE"
        ).fetchall()
        return [f["proveedor"] for f in filas]

    def _a_factura(self, fila: sqlite3.Row) -> FacturaCompra:
        lineas = self._con.execute(
            "SELECT * FROM facturas_compra_lineas WHERE factura_id = ? ORDER BY id", (fila["id"],)
        ).fetchall()
        return FacturaCompra(
            proveedor=fila["proveedor"],
            numero=fila["numero"],
            fecha=date.fromisoformat(fila["fecha"]),
            neto=fila["neto"],
            impuestos=fila["impuestos"],
            estado=EstadoFactura(fila["estado"]),
            id=fila["id"],
            lineas=[
                LineaFactura(
                    codigo_producto=x["codigo_producto"],
                    cantidad=Decimal(x["cantidad"]),
                    costo_unitario_neto=x["costo_unitario_neto"],
                    fecha_vencimiento=(
                        date.fromisoformat(x["fecha_vencimiento"])
                        if x["fecha_vencimiento"]
                        else None
                    ),
                    codigo_lote=x["codigo_lote"] or "",
                    costo_anterior=x["costo_anterior"],
                )
                for x in lineas
            ],
        )
