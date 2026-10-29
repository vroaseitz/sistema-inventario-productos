"""Ventana unica de la aplicacion (GEN-01): modulos F1 a F7 como el prototipo v3.

Una sola ventana con una franja de color por modulo y atajos F1-F7. Hoy solo Operacion
(venta y caja) y Catalogo (productos) tienen pantalla real; los demas modulos muestran
que historias de usuario los cubren y NO fingen funcionalidad que no existe.

Este archivo es la raiz de composicion: aqui se instancian las implementaciones concretas
(SQLite, Supabase) y se inyectan en los casos de uso y las pantallas.

Uso:
    python -m pos
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk

from pos.interfaz.app_inventario import VentanaInventario
from pos.interfaz.app_tkinter import VentanaProductos
from pos.interfaz.app_ventas import VentanaVentas


@dataclass(frozen=True)
class Modulo:
    clave: str  # atajo de teclado: F1..F7
    nombre: str
    color: str  # franja del modulo (colores del prototipo v3)
    historias: tuple[str, ...]
    implementado: bool = False


MODULOS: tuple[Modulo, ...] = (
    Modulo("F1", "Operacion", "#1D4E6F", ("HU-VTA-01 a 07", "HU-CAJ-01 a 04"), True),
    Modulo("F2", "Catalogo", "#8A5A17", ("HU-PRD-01 a 10",), True),
    Modulo("F3", "Inventario", "#5B3E7E", ("HU-INV-01 a 08",), True),
    Modulo("F4", "Clientes", "#2E6B3E", ("HU-CLI-01 a 05",)),
    Modulo("F5", "Compras", "#7A4A2E", ("HU-CMP-01 a 03",)),
    Modulo("F6", "Reportes", "#1E5F63", ("HU-REP-01 a 05",)),
    Modulo("F7", "Administracion", "#4A4F55", ("HU-USR-01, 03",)),
)


class _ModuloPendiente(ttk.Frame):
    """Marcador honesto de un modulo sin pantalla todavia."""

    def __init__(self, parent: tk.Misc, modulo: Modulo) -> None:
        super().__init__(parent)
        ttk.Label(self, text=modulo.nombre, font=("TkDefaultFont", 16, "bold")).pack(pady=(60, 8))
        ttk.Label(
            self,
            text="Este modulo todavia no tiene pantalla.\n"
            f"Historias de usuario: {', '.join(modulo.historias)}.",
            justify="center",
        ).pack()


class VentanaPrincipal(tk.Tk):
    def __init__(self, fabricas: dict[str, Callable[[tk.Misc], ttk.Frame]] | None = None) -> None:
        """`fabricas` mapea F1..F7 a una funcion que construye la pantalla dado su contenedor."""
        super().__init__()
        self.title("NaturalSur - Emporio")
        self.geometry("1100x760")
        self.minsize(980, 700)

        self._pestanas: dict[str, tk.Label] = {}
        self._marcos: dict[str, ttk.Frame] = {}
        self._activo: str | None = None

        barra = tk.Frame(self, bg="#f3f5f4")
        barra.pack(fill="x")
        tk.Label(
            barra, text="NaturalSur", bg="#f3f5f4", fg="#2f6b45", font=("TkDefaultFont", 13, "bold")
        ).pack(side="left", padx=14, pady=6)

        self._franja = tk.Frame(self, height=5, bg=MODULOS[0].color)
        self._franja.pack(fill="x")
        self._contenido = ttk.Frame(self)
        self._contenido.pack(fill="both", expand=True)

        fabricas = fabricas or {}
        for modulo in MODULOS:
            etiqueta = tk.Label(
                barra,
                text=f"{modulo.clave}  {modulo.nombre}",
                bg="#f3f5f4",
                fg="#1b2220",
                padx=12,
                pady=7,
                cursor="hand2",
            )
            etiqueta.pack(side="left")
            etiqueta.bind("<Button-1>", lambda _e, k=modulo.clave: self.mostrar(k))
            self._pestanas[modulo.clave] = etiqueta
            self.bind(f"<{modulo.clave}>", lambda _e, k=modulo.clave: self.mostrar(k))
            fabrica = fabricas.get(modulo.clave)
            self._marcos[modulo.clave] = (
                fabrica(self._contenido) if fabrica else _ModuloPendiente(self._contenido, modulo)
            )

        self.mostrar("F1")

    def mostrar(self, clave: str) -> None:
        """Cambia de modulo: muestra su pantalla y pinta la franja con su color."""
        if clave == self._activo or clave not in self._marcos:
            return
        if self._activo is not None:
            self._marcos[self._activo].pack_forget()
            self._pestanas[self._activo].config(bg="#f3f5f4", fg="#1b2220")
        modulo = next(m for m in MODULOS if m.clave == clave)
        self._marcos[clave].pack(fill="both", expand=True)
        self._pestanas[clave].config(bg=modulo.color, fg="#ffffff")
        self._franja.config(bg=modulo.color)
        self._activo = clave

    @property
    def modulo_activo(self) -> str | None:
        return self._activo


def construir_aplicacion() -> VentanaPrincipal:
    """Arma la app completa: repositorios SQLite, casos de uso, sincronizacion y pantallas."""
    from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
    from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
    from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import (
        ConsultarAlertasVencimiento,
    )
    from pos.aplicacion.casos_uso.editar_producto import EditarProducto
    from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
    from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja
    from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
    from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
    from pos.infraestructura.config import Config
    from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
    from pos.infraestructura.sqlite.conexion import crear_conexion
    from pos.infraestructura.sqlite.esquema import crear_esquema
    from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
    from pos.infraestructura.sqlite.repositorio_historial import RepositorioHistorialSQLite
    from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
    from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
    from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
    from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite
    from pos.infraestructura.supabase.adaptador_supabase import AdaptadorSupabase

    config = Config.desde_entorno()
    conexion = crear_conexion(config.sqlite_path)
    crear_esquema(conexion)

    repo_productos = RepositorioProductosSQLite(conexion)
    repo_existencias = RepositorioExistenciasSQLite(conexion)
    repo_turnos = RepositorioTurnosCajaSQLite(conexion)
    repo_ventas = RepositorioVentasSQLite(conexion)
    repo_historial = RepositorioHistorialSQLite(conexion)
    repo_lotes = RepositorioLotesSQLite(conexion)
    cola = ColaSincronizacionSQLite(conexion)
    # Sin SUPABASE_DB_URL la app vende igual y deja lo pendiente en la cola.
    publicador = AdaptadorSupabase(config.supabase_db_url) if config.supabase_db_url else None

    return VentanaPrincipal(
        {
            "F1": lambda padre: VentanaVentas(
                padre,
                repo_turnos,
                repo_productos,
                repo_ventas,
                RegistrarVenta(
                    repo_ventas,
                    repo_turnos,
                    repo_productos,
                    repo_existencias,
                    cola=cola,
                    repositorio_lotes=repo_lotes,
                ),
                AbrirTurnoCaja(repo_turnos, cola=cola),
                CerrarTurnoCaja(repo_turnos, repo_ventas, cola=cola),
                RegistrarMovimientoCaja(repo_turnos, cola=cola),
                cola=cola,
                publicador=publicador,
            ),
            "F2": lambda padre: VentanaProductos(
                padre,
                repo_productos,
                RegistrarProducto(repo_productos, cola=cola),
                EditarProducto(repo_productos, repo_historial),
            ),
            "F3": lambda padre: VentanaInventario(
                padre,
                repo_productos,
                IngresarStock(repo_productos, repo_existencias, repo_lotes, cola=cola),
                ConsultarAlertasVencimiento(repo_lotes, repo_productos),
            ),
        }
    )


def main() -> None:
    construir_aplicacion().mainloop()


if __name__ == "__main__":
    main()
