import sqlite3
from datetime import datetime

from pos.aplicacion.puertos import RepositorioHistorial
from pos.dominio.productos import RegistroCambioPrecio
from pos.dominio.value_objects import Dinero


class RepositorioHistorialSQLite(RepositorioHistorial):
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    def guardar_registro_precio(self, registro: RegistroCambioPrecio) -> None:
        query = """
            INSERT INTO historial_precios
            (codigo_producto, precio_anterior, precio_nuevo, usuario, fecha, motivo)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        parametros = (
            registro.codigo_producto,
            registro.precio_anterior.monto,
            registro.precio_nuevo.monto,
            registro.usuario,
            registro.fecha,
            registro.motivo,
        )
        cursor = self.conexion.cursor()
        cursor.execute(query, parametros)
        self.conexion.commit()

    def listar_por_producto(self, codigo: str) -> list[RegistroCambioPrecio]:
        """Cambios de precio del producto, el mas reciente primero (HU-PRD-05). No se editan."""
        filas = self.conexion.execute(
            "SELECT * FROM historial_precios WHERE codigo_producto = ? ORDER BY id DESC",
            (codigo,),
        ).fetchall()
        return [
            RegistroCambioPrecio(
                f["codigo_producto"],
                Dinero(f["precio_anterior"]),
                Dinero(f["precio_nuevo"]),
                f["usuario"],
                datetime.fromisoformat(str(f["fecha"])),
                f["motivo"] or "",
            )
            for f in filas
        ]
