"""Punto de entrada de la aplicacion de escritorio.

Actua como "raiz de composicion": es el unico lugar donde se instancian las
implementaciones concretas (SQLite) y se inyectan en los casos de uso y la GUI.
El resto del sistema solo conoce los puertos.

Uso:
    python -m pos
"""

from __future__ import annotations

from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.infraestructura.config import Config
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite


def main() -> None:
    config = Config.desde_entorno()
    conexion = crear_conexion(config.sqlite_path)
    crear_esquema(conexion)

    repositorio = RepositorioProductosSQLite(conexion)
    registrar = RegistrarProducto(repositorio)

    # Import diferido: la GUI (Tkinter) solo se carga al ejecutar, no al importar el
    # paquete, para que los tests del nucleo no dependan de un entorno grafico.
    from pos.interfaz.app_tkinter import VentanaProductos

    VentanaProductos(repositorio, registrar).mainloop()


if __name__ == "__main__":
    main()
