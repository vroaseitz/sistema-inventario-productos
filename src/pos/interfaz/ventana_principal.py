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

import time
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk

from pos.interfaz.app_administracion import VentanaAdministracion
from pos.interfaz.app_clientes import VentanaClientes
from pos.interfaz.app_compras import VentanaCompras
from pos.interfaz.app_inventario import VentanaInventario
from pos.interfaz.app_reportes import VentanaReportes
from pos.interfaz.app_tkinter import VentanaProductos
from pos.interfaz.app_ventas import VentanaVentas
from pos.interfaz.login import pedir_acceso
from pos.interfaz.sesion import Sesion


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
    Modulo("F4", "Clientes", "#2E6B3E", ("HU-CLI-01 a 05",), True),
    Modulo("F5", "Compras", "#7A4A2E", ("HU-CMP-01 a 03",), True),
    Modulo("F6", "Reportes", "#1E5F63", ("HU-REP-01 a 05",), True),
    Modulo("F7", "Administracion", "#4A4F55", ("HU-USR-01, 03",), True),
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

        self._permitidos: Callable[[], frozenset[str]] = lambda: frozenset(m.clave for m in MODULOS)
        self._ultima_actividad = time.monotonic()
        self._pestanas: dict[str, tk.Label] = {}
        self._marcos: dict[str, ttk.Frame] = {}
        self._activo: str | None = None

        # Fila de sesion arriba (usuario, clave, salir): no comparte fila con las pestanas F1-F7
        # porque a 1100 px de ancho las tapaba.
        barra_sesion = tk.Frame(self, bg="#e6eae8")
        barra_sesion.pack(fill="x")
        barra = tk.Frame(self, bg="#f3f5f4")
        barra.pack(fill="x")
        tk.Label(
            barra, text="NaturalSur", bg="#f3f5f4", fg="#2f6b45", font=("TkDefaultFont", 13, "bold")
        ).pack(side="left", padx=14, pady=6)

        # HU-USR-01: quien esta en el sistema, su clave y salir (a la derecha de la barra).
        self._btn_salir = tk.Label(
            barra_sesion, text="Cerrar sesión", bg="#e6eae8", fg="#4A4F55", padx=10, cursor="hand2"
        )
        self._btn_salir.pack(side="right")
        self._btn_clave = tk.Label(
            barra_sesion, text="Mi contraseña", bg="#e6eae8", fg="#4A4F55", padx=10, cursor="hand2"
        )
        self._btn_clave.pack(side="right")
        self._lbl_usuario = tk.Label(barra_sesion, text="", bg="#e6eae8", fg="#1b2220", padx=10)
        self._lbl_usuario.pack(side="right")
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
        if clave not in self._permitidos():
            return  # HU-USR-02: la vendedora no entra a los modulos de la administradora
        if self._activo is not None:
            self._marcos[self._activo].pack_forget()
            self._pestanas[self._activo].config(bg="#f3f5f4", fg="#1b2220")
        modulo = next(m for m in MODULOS if m.clave == clave)
        self._marcos[clave].pack(fill="both", expand=True)
        # R-02: las pantallas que dependen de lo que pasa en otras se refrescan al entrar.
        al_mostrar = getattr(self._marcos[clave], "al_mostrar", None)
        if callable(al_mostrar):
            al_mostrar()
        self._pestanas[clave].config(bg=modulo.color, fg="#ffffff")
        self._franja.config(bg=modulo.color)
        self._activo = clave

    # ------------------------------------------------------- sesion y permisos (F7) --

    def configurar_sesion(
        self,
        permitidos: Callable[[], frozenset[str]],
        al_cambiar_clave: Callable[[], None],
        al_cerrar_sesion: Callable[[], None],
    ) -> None:
        self._permitidos = permitidos
        self._btn_clave.bind("<Button-1>", lambda _e: al_cambiar_clave())
        self._btn_salir.bind("<Button-1>", lambda _e: al_cerrar_sesion())
        self.refrescar_permisos()

    def mostrar_usuario(self, texto: str) -> None:
        self._lbl_usuario.config(text=texto)

    def refrescar_permisos(self) -> None:
        """Atenúa los modulos que el perfil no puede usar y vuelve a F1 si el actual ya no vale."""
        permitidos = self._permitidos()
        for modulo in MODULOS:
            etiqueta = self._pestanas[modulo.clave]
            if modulo.clave in permitidos:
                if modulo.clave != self._activo:
                    etiqueta.config(fg="#1b2220")
            else:
                etiqueta.config(fg="#b5b9b8", cursor="arrow")
        if self._activo is not None and self._activo not in permitidos:
            anterior, self._activo = self._activo, None
            self._marcos[anterior].pack_forget()
            self._pestanas[anterior].config(bg="#f3f5f4")
            self.mostrar("F1")

    def vigilar_inactividad(
        self, minutos: Callable[[], int], al_vencer: Callable[[], None], cada_ms: int = 10_000
    ) -> None:
        """Cierre de sesion por inactividad (HU-USR-01): sin teclas ni clics, pide la clave."""

        def actividad(_evento: object = None) -> None:
            self._ultima_actividad = time.monotonic()

        for evento in ("<Key>", "<Button>", "<Motion>"):
            self.bind_all(evento, actividad, add="+")

        def revisar() -> None:
            limite = minutos() * 60
            if limite > 0 and time.monotonic() - self._ultima_actividad >= limite:
                al_vencer()
                self._ultima_actividad = time.monotonic()
            self.after(cada_ms, revisar)

        self.after(cada_ms, revisar)

    @property
    def modulo_activo(self) -> str | None:
        return self._activo


def construir_aplicacion(con_login: bool = False) -> VentanaPrincipal:
    """Arma la app completa: repositorios SQLite, casos de uso, sincronizacion y pantallas."""
    from pos.aplicacion.auditor import Auditor
    from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
    from pos.aplicacion.casos_uso.autenticar_usuario import AutenticarUsuario, CrearUsuario
    from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
    from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import (
        ConsultarAlertasVencimiento,
    )
    from pos.aplicacion.casos_uso.editar_producto import EditarProducto
    from pos.aplicacion.casos_uso.gestionar_clientes import GestionarClientes, RegistrarAbono
    from pos.aplicacion.casos_uso.gestionar_usuarios import GestionarUsuarios
    from pos.aplicacion.casos_uso.imprimir_comprobante import ImprimirComprobante
    from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
    from pos.aplicacion.casos_uso.registrar_factura_compra import RegistrarFacturaCompra
    from pos.aplicacion.casos_uso.registrar_merma import RegistrarMerma
    from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja
    from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
    from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
    from pos.aplicacion.casos_uso.reporte_ventas import ReporteVentas
    from pos.dominio.usuarios import NOMBRES_ROL, Rol, modulos_permitidos
    from pos.infraestructura.config import Config
    from pos.infraestructura.impresion.impresoras import crear_impresora
    from pos.infraestructura.seguridad.hasheador_bcrypt import HasheadorBcrypt
    from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
    from pos.infraestructura.sqlite.conexion import crear_conexion
    from pos.infraestructura.sqlite.esquema import crear_esquema
    from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
    from pos.infraestructura.sqlite.repositorio_categorias import RepositorioCategoriasSQLite
    from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite
    from pos.infraestructura.sqlite.repositorio_configuracion import (
        RepositorioConfiguracionSQLite,
    )
    from pos.infraestructura.sqlite.repositorio_existencias import (
        RepositorioAjustesSQLite,
        RepositorioExistenciasSQLite,
    )
    from pos.infraestructura.sqlite.repositorio_facturas_compra import (
        RepositorioFacturasCompraSQLite,
    )
    from pos.infraestructura.sqlite.repositorio_historial import RepositorioHistorialSQLite
    from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
    from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
    from pos.infraestructura.sqlite.repositorio_tickets_espera import (
        RepositorioTicketsEsperaSQLite,
    )
    from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
    from pos.infraestructura.sqlite.repositorio_usuarios import RepositorioUsuariosSQLite
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
    repo_categorias = RepositorioCategoriasSQLite(conexion)
    repo_usuarios = RepositorioUsuariosSQLite(conexion)
    repo_facturas = RepositorioFacturasCompraSQLite(conexion)
    repo_clientes = RepositorioClientesSQLite(conexion)
    cola = ColaSincronizacionSQLite(conexion)
    sesion = Sesion()
    hasheador = HasheadorBcrypt()
    repo_auditoria = RepositorioAuditoriaSQLite(conexion)
    repo_config = RepositorioConfiguracionSQLite(conexion)
    # HU-USR-03: el nombre sale de la sesion en el momento de cada cambio (la sesion puede cambiar).
    auditor = Auditor(repo_auditoria, lambda: sesion.nombre)
    gestion_usuarios = GestionarUsuarios(repo_usuarios, hasheador, auditor)
    carpeta_comprobantes = Path(config.sqlite_path).resolve().parent / "comprobantes"
    imprimir = ImprimirComprobante(
        lambda: crear_impresora(
            repo_config.obtener_texto("impresora_nombre"), carpeta_comprobantes
        ),
        repo_productos,
        repo_ventas,
        repo_config,
        repo_clientes,
        cajera=lambda: sesion.nombre,
    )
    # Sin SUPABASE_DB_URL la app vende igual y deja lo pendiente en la cola.
    publicador = AdaptadorSupabase(config.supabase_db_url) if config.supabase_db_url else None

    ventana = VentanaPrincipal(
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
                    repositorio_clientes=repo_clientes,
                ),
                AbrirTurnoCaja(repo_turnos, cola=cola),
                CerrarTurnoCaja(
                    repo_turnos, repo_ventas, cola=cola, repositorio_clientes=repo_clientes
                ),
                RegistrarMovimientoCaja(repo_turnos, cola=cola),
                cola=cola,
                publicador=publicador,
                sesion=sesion,
                repo_tickets=RepositorioTicketsEsperaSQLite(conexion),
                auditoria=repo_auditoria,
                repo_clientes=repo_clientes,
                configuracion=repo_config,
                imprimir=imprimir,
            ),
            "F2": lambda padre: VentanaProductos(
                padre,
                repo_productos,
                RegistrarProducto(
                    repo_productos,
                    cola=cola,
                    repositorio_categorias=repo_categorias,
                    auditor=auditor,
                ),
                EditarProducto(
                    repo_productos,
                    repo_historial,
                    cola=cola,
                    repositorio_categorias=repo_categorias,
                    auditor=auditor,
                ),
                repo_categorias,
                sesion=sesion,
            ),
            "F4": lambda padre: VentanaClientes(
                padre,
                GestionarClientes(repo_clientes),
                RegistrarAbono(repo_clientes, repo_turnos),
                repo_clientes,
            ),
            "F5": lambda padre: VentanaCompras(
                padre,
                RegistrarFacturaCompra(
                    repo_facturas,
                    repo_productos,
                    repo_existencias,
                    repo_lotes,
                    cola=cola,
                    repositorio_categorias=repo_categorias,
                    auditor=auditor,
                ),
                repo_facturas,
                repo_productos,
            ),
            "F6": lambda padre: VentanaReportes(
                padre, ReporteVentas(repo_ventas, repo_productos), repo_categorias
            ),
            "F3": lambda padre: VentanaInventario(
                padre,
                repo_productos,
                IngresarStock(repo_productos, repo_existencias, repo_lotes, cola=cola),
                ConsultarAlertasVencimiento(repo_lotes, repo_productos, configuracion=repo_config),
                repo_lotes,
                registrar_merma=RegistrarMerma(
                    repo_existencias,
                    RepositorioAjustesSQLite(conexion),
                    repositorio_lotes=repo_lotes,
                    cola=cola,
                    auditor=auditor,
                ),
                repo_existencias=repo_existencias,
                sesion=sesion,
            ),
            "F7": lambda padre: VentanaAdministracion(
                padre,
                gestion_usuarios,
                repo_usuarios,
                repo_auditoria,
                repo_config,
                auditor=auditor,
                sesion=sesion,
                cola=cola,
                con_supabase=publicador is not None,
                imprimir=imprimir,
            ),
        }
    )
    if con_login:
        from pos.interfaz.acceso import dialogo_cambiar_clave

        def pedir_ingreso():
            """Cuadro de acceso sobre una cubierta lisa. Sirve al abrir y al cerrar sesion."""
            primer_uso = not repo_usuarios.hay_usuarios()
            if primer_uso:
                # El primer usuario es la administradora; las demas personas las crea ella en F7.
                def accion(nombre: str, clave: str):
                    CrearUsuario(repo_usuarios, hasheador).ejecutar(nombre, clave, Rol.ADMIN)
                    return AutenticarUsuario(repo_usuarios, hasheador).ejecutar(nombre, clave)
            else:
                accion = AutenticarUsuario(repo_usuarios, hasheador).ejecutar
            # A-03: la ventana principal NO se oculta (en Windows un cuadro asociado a una ventana
            # oculta tampoco se ve y queda todo en negro). Se tapa con una cubierta lisa.
            cubierta = tk.Frame(ventana, bg="#f3f5f4")
            cubierta.place(x=0, y=0, relwidth=1, relheight=1)
            ventana.update()
            usuario = pedir_acceso(ventana, accion, primer_uso)
            cubierta.destroy()
            return usuario

        def aplicar_usuario(usuario) -> None:
            sesion.usuario_id, sesion.nombre, sesion.rol = usuario.id, usuario.nombre, usuario.rol
            ventana.title(f"NaturalSur - Emporio ({usuario.nombre})")
            ventana.mostrar_usuario(f"{usuario.nombre} · {NOMBRES_ROL[usuario.rol]}")
            ventana.refrescar_permisos()

        def cerrar_sesion() -> None:
            usuario = pedir_ingreso()
            if usuario is None:
                ventana.destroy()  # sin entrar de nuevo no se queda abierta: los tickets se guardan
                return
            aplicar_usuario(usuario)

        def cambiar_mi_clave() -> None:
            dialogo_cambiar_clave(ventana, sesion.nombre, gestion_usuarios)

        ventana.configurar_sesion(
            lambda: modulos_permitidos(sesion.rol), cambiar_mi_clave, cerrar_sesion
        )
        ventana.vigilar_inactividad(
            lambda: repo_config.obtener("inactividad_minutos"), cerrar_sesion
        )
        usuario = pedir_ingreso()
        if usuario is None:
            ventana.destroy()
            raise SystemExit(0)
        aplicar_usuario(usuario)
    return ventana


def main() -> None:
    construir_aplicacion(con_login=True).mainloop()


if __name__ == "__main__":
    main()
