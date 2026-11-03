"""Pantalla F7 Administracion: usuarios y perfiles, auditoria y configuracion.

Cubre HU-USR-01 (usuarios, claves), HU-USR-02 (perfiles), HU-USR-03 (auditoria de cambios, solo
lectura) y los parametros de operacion de la Configuracion del prototipo v3. La impresora y el
cajon (HU-VTA-06) siguen pendientes y asi se dicen.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.gestionar_usuarios import GestionarUsuarios
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioAuditoria,
    RepositorioConfiguracion,
    RepositorioUsuarios,
)
from pos.dominio.configuracion import PARAMETROS, validar_parametro
from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_clp
from pos.dominio.usuarios import MODULOS_POR_ROL, NOMBRES_ROL, Rol
from pos.interfaz.campo_fecha import CampoFecha
from pos.interfaz.dialogo_formulario import pedir_formulario
from pos.interfaz.sesion import Sesion

ROL_POR_NOMBRE = {nombre: rol for rol, nombre in NOMBRES_ROL.items()}
ETIQUETAS_ANTIGUAS = {
    "tickets_descartados_al_cerrar_jornada": "Tickets descartados al cerrar la jornada"
}

# Lo que puede hacer cada perfil (HU-USR-02), tal como el prototipo v3.
FUNCIONES = (
    ("Registrar ventas y cobrar", True, True),
    ("Abrir y cerrar la jornada de caja", True, True),
    ("Consultar productos", True, True),
    ("Crear, modificar o desactivar productos", True, False),
    ("Registrar mermas y ajustes", True, False),
    ("Registrar facturas de compra", True, False),
    ("Ver reportes y clientes", True, False),
    ("Administrar usuarios y ver auditoría", True, False),
)


def _hora(valor: datetime | None) -> str:
    return valor.strftime("%d-%m-%Y %H:%M") if valor else "—"


class VentanaAdministracion(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        gestion: GestionarUsuarios,
        repo_usuarios: RepositorioUsuarios,
        repo_auditoria: RepositorioAuditoria,
        configuracion: RepositorioConfiguracion,
        auditor: Auditor | None = None,
        sesion: Sesion | None = None,
        cola: ColaSincronizacion | None = None,
        con_supabase: bool = False,
    ) -> None:
        super().__init__(parent, padding=8)
        self._gestion = gestion
        self._usuarios = repo_usuarios
        self._auditoria = repo_auditoria
        self._config = configuracion
        self._auditor = auditor
        self._sesion = sesion or Sesion()
        self._cola = cola
        self._con_supabase = con_supabase
        self._mensaje = tk.StringVar()

        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True)
        self._construir_usuarios()
        self._construir_auditoria()
        self._construir_configuracion()
        ttk.Label(self, textvariable=self._mensaje, foreground="#4A4F55").pack(anchor="w", pady=4)
        self.refrescar()

    # ------------------------------------------------------------------ usuarios --

    def _construir_usuarios(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Usuarios y perfiles")
        botones = ttk.Frame(marco)
        botones.pack(fill="x")
        for texto, comando in (
            ("Nuevo usuario", self._dialogo_nuevo),
            ("Restablecer contraseña", self._dialogo_clave),
            ("Cambiar perfil", self._dialogo_perfil),
            ("Desactivar / reactivar", self._cambiar_estado),
        ):
            ttk.Button(botones, text=texto, command=comando).pack(side="left", padx=4, pady=4)
        self._tabla_usuarios = ttk.Treeview(
            marco, columns=("usuario", "perfil", "acceso", "estado"), show="headings", height=6
        )
        for clave, titulo, ancho in (
            ("usuario", "Usuario", 180),
            ("perfil", "Perfil", 140),
            ("acceso", "Último acceso", 160),
            ("estado", "Estado", 100),
        ):
            self._tabla_usuarios.heading(clave, text=titulo)
            self._tabla_usuarios.column(clave, width=ancho, anchor="w")
        self._tabla_usuarios.pack(fill="x", pady=4)
        ttk.Label(marco, text="Qué puede hacer cada perfil", font=("", 11, "bold")).pack(
            anchor="w", pady=(10, 2)
        )
        matriz = ttk.Treeview(
            marco, columns=("funcion", "admin", "vend"), show="headings", height=len(FUNCIONES)
        )
        for clave, titulo, ancho in (
            ("funcion", "Función", 320),
            ("admin", "Administradora", 120),
            ("vend", "Vendedora", 120),
        ):
            matriz.heading(clave, text=titulo)
            matriz.column(clave, width=ancho, anchor="w" if clave == "funcion" else "center")
        for funcion, admin, vend in FUNCIONES:
            matriz.insert(
                "", "end", values=(funcion, "Sí" if admin else "No", "Sí" if vend else "No")
            )
        matriz.pack(fill="x")
        ttk.Label(
            marco,
            text="La vendedora solo ve F1 Operación (módulos permitidos: "
            + ", ".join(sorted(MODULOS_POR_ROL[Rol.CAJERO]))
            + ").",
            foreground="#666",
        ).pack(anchor="w", pady=4)

    def _usuario_elegido(self) -> str | None:
        seleccion = self._tabla_usuarios.selection()
        if not seleccion:
            messagebox.showwarning("Usuarios", "Elige un usuario de la lista")
            return None
        return seleccion[0]

    def _ejecutar(self, accion, exito: str) -> bool:
        try:
            accion()
        except ErrorDominio as error:
            messagebox.showerror("Usuarios", str(error))
            return False
        self._mensaje.set(exito)
        self.refrescar()
        return True

    def crear_usuario(self, nombre: str, clave: str, repetir: str, perfil: str) -> bool:
        rol = ROL_POR_NOMBRE.get(perfil)
        if rol is None:
            messagebox.showerror("Usuarios", "Elige el perfil del usuario")
            return False
        return self._ejecutar(
            lambda: self._gestion.crear(nombre, clave, repetir, rol),
            f"Usuario creado: {nombre.strip().lower()}",
        )

    def restablecer_clave(self, nombre: str, nueva: str, repetir: str) -> bool:
        return self._ejecutar(
            lambda: self._gestion.restablecer_clave(nombre, nueva, repetir),
            f"Contraseña de {nombre} restablecida",
        )

    def cambiar_perfil(self, nombre: str, perfil: str) -> bool:
        rol = ROL_POR_NOMBRE.get(perfil)
        if rol is None:
            messagebox.showerror("Usuarios", "Elige el perfil")
            return False
        return self._ejecutar(
            lambda: self._gestion.cambiar_perfil(nombre, rol), f"{nombre} ahora es {perfil}"
        )

    def cambiar_estado(self, nombre: str) -> bool:
        usuario = self._usuarios.obtener_por_nombre(nombre)
        return self._ejecutar(
            lambda: self._gestion.cambiar_estado(nombre, not usuario.activo, self._sesion.nombre),
            f"{nombre} quedó {'inactivo' if usuario.activo else 'activo'}",
        )

    def _dialogo_nuevo(self) -> None:
        pedir_formulario(
            self,
            "Nuevo usuario",
            [
                ("nombre", "Usuario", "", None),
                ("clave", "Contraseña (mínimo 8)", "", "clave"),
                ("repetir", "Repetir contraseña", "", "clave"),
                ("perfil", "Perfil", "Vendedora", list(ROL_POR_NOMBRE)),
            ],
            lambda v: self.crear_usuario(v["nombre"], v["clave"], v["repetir"], v["perfil"]),
            "Crear usuario",
        )

    def _dialogo_clave(self) -> None:
        nombre = self._usuario_elegido()
        if nombre is None:
            return
        pedir_formulario(
            self,
            f"Restablecer contraseña de {nombre}",
            [("nueva", "Contraseña nueva", "", "clave"), ("repetir", "Repetir", "", "clave")],
            lambda v: self.restablecer_clave(nombre, v["nueva"], v["repetir"]),
            "Restablecer",
        )

    def _dialogo_perfil(self) -> None:
        nombre = self._usuario_elegido()
        if nombre is None:
            return
        actual = NOMBRES_ROL[self._usuarios.obtener_por_nombre(nombre).rol]
        pedir_formulario(
            self,
            f"Cambiar perfil de {nombre}",
            [("perfil", "Perfil", actual, list(ROL_POR_NOMBRE))],
            lambda v: self.cambiar_perfil(nombre, v["perfil"]),
            "Cambiar perfil",
        )

    def _cambiar_estado(self) -> None:
        nombre = self._usuario_elegido()
        if nombre is not None:
            self.cambiar_estado(nombre)

    # ----------------------------------------------------------------- auditoria --

    def _construir_auditoria(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Auditoría")
        filtros = ttk.Frame(marco)
        filtros.pack(fill="x")
        self._f_usuario = tk.StringVar(value="Todos")
        self._f_operacion = tk.StringVar(value="Todas")
        ttk.Label(filtros, text="Usuario").grid(row=0, column=0, sticky="w", padx=4)
        self._combo_usuario = ttk.Combobox(
            filtros, textvariable=self._f_usuario, state="readonly", width=16
        )
        self._combo_usuario.grid(row=1, column=0, padx=4)
        ttk.Label(filtros, text="Desde").grid(row=0, column=1, sticky="w", padx=4)
        self._f_desde = CampoFecha(filtros, date.today() - timedelta(days=30), width=12)
        self._f_desde.grid(row=1, column=1, padx=4)
        ttk.Label(filtros, text="Hasta").grid(row=0, column=2, sticky="w", padx=4)
        self._f_hasta = CampoFecha(filtros, date.today(), width=12)
        self._f_hasta.grid(row=1, column=2, padx=4)
        ttk.Label(filtros, text="Operación").grid(row=0, column=3, sticky="w", padx=4)
        self._combo_operacion = ttk.Combobox(
            filtros, textvariable=self._f_operacion, state="readonly", width=34
        )
        self._combo_operacion.grid(row=1, column=3, padx=4)
        ttk.Button(filtros, text="Buscar", command=self._refrescar_auditoria).grid(
            row=1, column=4, padx=8
        )
        columnas = ("fecha", "usuario", "operacion", "registro", "antes", "despues")
        self._tabla_auditoria = ttk.Treeview(marco, columns=columnas, show="headings", height=14)
        for clave, titulo, ancho in (
            ("fecha", "Fecha y hora", 130),
            ("usuario", "Usuario", 90),
            ("operacion", "Operación", 200),
            ("registro", "Registro", 230),
            ("antes", "Antes", 100),
            ("despues", "Después", 100),
        ):
            self._tabla_auditoria.heading(clave, text=titulo)
            self._tabla_auditoria.column(clave, width=ancho, anchor="w")
        self._tabla_auditoria.pack(fill="both", expand=True, pady=8)
        ttk.Label(
            marco,
            text="Solo lectura: un registro no se edita ni se borra. Ahí queda de dónde salió "
            "un dato raro.",
            foreground="#666",
        ).pack(anchor="w")

    def consultar_auditoria(self) -> list[dict]:
        try:
            desde = datetime.strptime(self._f_desde.get().strip(), "%Y-%m-%d").date()
            hasta = datetime.strptime(self._f_hasta.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Auditoría", "Las fechas deben ser AAAA-MM-DD")
            return []
        usuario = None if self._f_usuario.get() == "Todos" else self._f_usuario.get()
        filas = self._auditoria.listar(usuario=usuario, desde=desde, hasta=hasta)
        operacion = self._f_operacion.get()
        if operacion != "Todas":
            filas = [f for f in filas if self._rotulo(f["accion"]) == operacion]
        return filas

    @staticmethod
    def _rotulo(accion: str) -> str:
        return ETIQUETAS_ANTIGUAS.get(accion, accion)

    def _refrescar_auditoria(self) -> None:
        todas = self._auditoria.listar()
        self._combo_usuario.config(values=["Todos"] + sorted({f["usuario"] for f in todas}))
        self._combo_operacion.config(
            values=["Todas"] + sorted({self._rotulo(f["accion"]) for f in todas})
        )
        self._tabla_auditoria.delete(*self._tabla_auditoria.get_children())
        for fila in self.consultar_auditoria():
            self._tabla_auditoria.insert(
                "",
                "end",
                values=(
                    datetime.fromisoformat(fila["fecha"]).strftime("%d-%m-%Y %H:%M"),
                    fila["usuario"],
                    self._rotulo(fila["accion"]),
                    fila["registro"],
                    fila["antes"],
                    fila["despues"],
                ),
            )

    # ------------------------------------------------------------- configuracion --

    def _construir_configuracion(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Configuración")
        reglas = ttk.LabelFrame(marco, text="Reglas de operación", padding=10)
        reglas.pack(fill="x")
        self._vars_config: dict[str, tk.StringVar] = {}
        for fila, parametro in enumerate(PARAMETROS):
            ttk.Label(reglas, text=f"{parametro.titulo} ({parametro.unidad})").grid(
                row=fila, column=0, sticky="w", padx=4, pady=4
            )
            self._vars_config[parametro.clave] = tk.StringVar()
            ttk.Entry(reglas, textvariable=self._vars_config[parametro.clave], width=12).grid(
                row=fila, column=1, padx=8
            )
            ttk.Label(reglas, text=parametro.ayuda, foreground="#666", wraplength=520).grid(
                row=fila, column=2, sticky="w", padx=4
            )
        ttk.Label(reglas, text="Redondeo en efectivo").grid(
            row=len(PARAMETROS), column=0, sticky="w", padx=4, pady=4
        )
        ttk.Label(reglas, text="A la decena (HU-VTA-04, regla fija)").grid(
            row=len(PARAMETROS), column=1, columnspan=2, sticky="w", padx=8
        )
        botones = ttk.Frame(marco)
        botones.pack(fill="x", pady=8)
        ttk.Button(botones, text="Guardar cambios", command=self.guardar_configuracion).pack(
            side="left", padx=4
        )
        ttk.Button(
            botones, text="Restaurar valores por defecto", command=self.restaurar_configuracion
        ).pack(side="left", padx=4)
        estado = ttk.LabelFrame(marco, text="Sincronización y equipos", padding=10)
        estado.pack(fill="x")
        self._lbl_conexion = ttk.Label(estado, text="")
        self._lbl_conexion.pack(anchor="w")
        self._lbl_pendientes = ttk.Label(estado, text="")
        self._lbl_pendientes.pack(anchor="w")
        ttk.Label(
            estado,
            text="Impresora de comprobantes y cajón de dinero: pendientes (HU-VTA-06), todavía "
            "no se construye la impresión.",
            foreground="#a11",
        ).pack(anchor="w", pady=(6, 0))

    def _refrescar_configuracion(self) -> None:
        for parametro in PARAMETROS:
            self._vars_config[parametro.clave].set(str(self._config.obtener(parametro.clave)))
        self._lbl_conexion.config(
            text="Estado de la conexión: "
            + ("Supabase configurado" if self._con_supabase else "sin Supabase (modo local)")
        )
        pendientes = len(self._cola.pendientes()) if self._cola is not None else 0
        self._lbl_pendientes.config(text=f"Operaciones pendientes de enviar: {pendientes}")

    def guardar_configuracion(self) -> bool:
        nuevos = {}
        for parametro in PARAMETROS:
            try:
                nuevos[parametro.clave] = validar_parametro(
                    parametro.clave, self._vars_config[parametro.clave].get()
                )
            except ErrorDominio as error:
                messagebox.showerror("Configuración", str(error))
                return False
        for parametro in PARAMETROS:
            antes = self._config.obtener(parametro.clave)
            despues = nuevos[parametro.clave]
            if antes == despues:
                continue
            self._config.guardar(parametro.clave, despues)
            if self._auditor is not None:
                formato = formatear_clp if parametro.unidad == "CLP" else str
                self._auditor.registrar(
                    "Cambio de configuración",
                    parametro.titulo,
                    formato(antes),
                    formato(despues),
                )
        self._mensaje.set("Configuración guardada")
        self.refrescar()
        return True

    def restaurar_configuracion(self) -> None:
        self._config.restaurar_valores_por_defecto()
        if self._auditor is not None:
            self._auditor.registrar(
                "Cambio de configuración", "Valores por defecto", "", "restaurados"
            )
        self._mensaje.set("Valores por defecto restaurados")
        self.refrescar()

    # ------------------------------------------------------------------ refresco --

    def refrescar(self) -> None:
        self._tabla_usuarios.delete(*self._tabla_usuarios.get_children())
        for usuario in self._usuarios.listar():
            self._tabla_usuarios.insert(
                "",
                "end",
                iid=usuario.nombre,
                values=(
                    usuario.nombre,
                    NOMBRES_ROL[usuario.rol],
                    _hora(usuario.ultimo_acceso),
                    "Activo" if usuario.activo else "Inactivo",
                ),
            )
        self._refrescar_auditoria()
        self._refrescar_configuracion()

    def al_mostrar(self) -> None:
        self.refrescar()
