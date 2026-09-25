import sqlite3
from pos.aplicacion.puertos import RepositorioHistorial
from pos.dominio.productos import RegistroCambioPrecio

class RepositorioHistorialSQLite(RepositorioHistorial):
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    def guardar_registro_precio(self, registro: RegistroCambioPrecio) -> None:
        query = """
            INSERT INTO historial_precios 
            (codigo_producto, precio_anterior, precio_nuevo, usuario, fecha)
            VALUES (?, ?, ?, ?, ?)
        """
        
        # OJO: Asumimos que tu Value Object 'Dinero' expone el número a través 
        # de una propiedad como '.monto' o '.valor'. Ajusta ese nombre según corresponda.
        parametros = (
            registro.codigo_producto,
            registro.precio_anterior.monto, 
            registro.precio_nuevo.monto,
            registro.usuario,
            registro.fecha
        )
        
        cursor = self.conexion.cursor()
        cursor.execute(query, parametros)
        self.conexion.commit()