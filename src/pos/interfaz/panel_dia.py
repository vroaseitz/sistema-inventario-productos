"""Resumen del dia de F1 (prototipo v3): como va la jornada al abrir el sistema.

Tarjetas con la venta de hoy y de la semana, la ganancia y la meta; la venta por medio de pago, lo
que mas ganancia aporta y lo que necesita atencion. «Configurar meta diaria» guarda las metas de
venta por tipo de dia (HU-REP-05).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.resumen_del_dia import TIPOS_DE_DIA, ResumenDelDia
from pos.aplicacion.puertos import RepositorioConfiguracion
from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_clp
from pos.dominio.pagos import NOMBRES_MEDIO
from pos.interfaz.dialogo_formulario import pedir_formulario
from pos.interfaz.tema import (
    ALERTA_FONDO,
    LINEA_2,
    MODULOS_COLOR,
    PAPEL,
    TINTA_2,
    BotonAccion,
    fuente,
)


def _tarjeta(padre: tk.Misc, titulo: str) -> tuple[tk.Label, tk.Label]:
    marco = tk.Frame(padre, bg=PAPEL, highlightthickness=1, highlightbackground=LINEA_2)
    marco.pack(side="left", fill="x", expand=True, padx=(0, 10))
    tk.Label(marco, text=titulo, bg=PAPEL, fg=TINTA_2, font=fuente(10)).pack(
        anchor="w", padx=12, pady=(10, 0)
    )
    valor = tk.Label(marco, text="—", bg=PAPEL, fg=MODULOS_COLOR["F1"][0], font=fuente(22, True))
    valor.pack(anchor="w", padx=12)
    detalle = tk.Label(marco, text="", bg=PAPEL, fg=TINTA_2, font=fuente(10))
    detalle.pack(anchor="w", padx=12, pady=(0, 10))
    return valor, detalle


class PanelDelDia(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        resumen: ResumenDelDia,
        configuracion: RepositorioConfiguracion,
        auditor: Auditor | None = None,
        ir_a_venta: Callable[[], None] | None = None,
        ir_a: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._resumen = resumen
        self._config = configuracion
        self._auditor = auditor
        self._ir_a = ir_a
        color, claro = MODULOS_COLOR["F1"]

        acciones = tk.Frame(self, bg=claro)
        acciones.pack(fill="x")
        interior = tk.Frame(acciones, bg=claro)
        interior.pack(fill="x", padx=12, pady=8)
        BotonAccion(
            interior, "Ir a la venta", ir_a_venta or (lambda: None), "F1", "primario", color
        ).pack(side="left", padx=(0, 6))
        BotonAccion(
            interior, "Configurar meta diaria", self._dialogo_meta, "", "normal", color, PAPEL
        ).pack(side="left", padx=6)
        BotonAccion(
            interior,
            "Ver reportes",
            lambda: self._navegar("reportes"),
            "F6",
            "normal",
            color,
            PAPEL,
        ).pack(side="left", padx=6)

        tarjetas = tk.Frame(self, bg=PAPEL)
        tarjetas.pack(fill="x", padx=12, pady=(12, 4))
        self._v_hoy, self._d_hoy = _tarjeta(tarjetas, "Venta de hoy")
        self._v_semana, self._d_semana = _tarjeta(tarjetas, "Venta de la semana")
        self._v_ganancia, self._d_ganancia = _tarjeta(tarjetas, "Ganancia de hoy")
        self._v_meta, self._d_meta = _tarjeta(tarjetas, "Meta de la jornada")

        centro = tk.Frame(self, bg=PAPEL)
        centro.pack(fill="x", padx=12, pady=6)
        izquierda = ttk.LabelFrame(centro, text="Venta por medio de pago", padding=8)
        izquierda.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._tabla_resumen = ttk.Treeview(
            izquierda, columns=("medio", "monto", "ventas"), show="headings", height=4
        )
        for clave, titulo, ancho, ancla in (
            ("medio", "Medio", 160, "w"),
            ("monto", "Monto", 110, "e"),
            ("ventas", "Ventas", 70, "e"),
        ):
            self._tabla_resumen.heading(clave, text=titulo)
            self._tabla_resumen.column(clave, width=ancho, anchor=ancla)
        self._tabla_resumen.pack(fill="x")
        derecha = ttk.LabelFrame(centro, text="Mayor aporte de ganancia", padding=8)
        derecha.pack(side="left", fill="both", expand=True)
        self._tabla_ganancia = ttk.Treeview(
            derecha, columns=("producto", "ganancia"), show="headings", height=4
        )
        self._tabla_ganancia.heading("producto", text="Producto")
        self._tabla_ganancia.heading("ganancia", text="Ganancia")
        self._tabla_ganancia.column("producto", width=230, anchor="w")
        self._tabla_ganancia.column("ganancia", width=110, anchor="e")
        self._tabla_ganancia.pack(fill="x")

        atencion = ttk.LabelFrame(self, text="Necesita atención hoy", padding=8)
        atencion.pack(fill="x", padx=12, pady=6)
        self._tabla_avisos = ttk.Treeview(
            atencion, columns=("aviso", "detalle", "accion"), show="headings", height=3
        )
        for clave, titulo, ancho, ancla in (
            ("aviso", "Aviso", 230, "w"),
            ("detalle", "Detalle", 420, "w"),
            ("accion", "Acción", 140, "w"),
        ):
            self._tabla_avisos.heading(clave, text=titulo)
            self._tabla_avisos.column(clave, width=ancho, anchor=ancla)
        self._tabla_avisos.tag_configure("urgente", background=ALERTA_FONDO)
        self._tabla_avisos.pack(fill="x")
        self._tabla_avisos.bind("<Double-Button-1>", lambda _e: self._abrir_aviso())
        # O-39: «Ver →» se presiona con un clic (columna Accion); la fila sigue con doble clic.
        self._tabla_avisos.bind("<ButtonRelease-1>", self._al_clic_en_aviso)
        self._destinos: dict[str, str] = {}
        self._lbl_resumen_dia = tk.Label(self, text="", bg=PAPEL, fg=TINTA_2)
        self._lbl_resumen_dia.pack(anchor="w", padx=14)
        tk.Label(
            self,
            text="La meta es sobre el monto vendido y depende del tipo de día: lunes a viernes, "
            "sábado y domingo. Se puede cambiar en «Configurar meta diaria».",
            bg=PAPEL,
            fg=TINTA_2,
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(2, 8))
        self.refrescar()

    def refrescar(self) -> None:
        r = self._resumen.ejecutar()
        self._v_hoy.config(text=formatear_clp(r.venta_hoy))
        self._d_hoy.config(text=f"{r.transacciones} transacciones")
        self._v_semana.config(text=formatear_clp(r.venta_semana))
        self._d_semana.config(text=f"{r.jornadas_semana} jornadas")
        self._v_ganancia.config(text=formatear_clp(r.ganancia_hoy))
        self._d_ganancia.config(
            text="sin ventas con costo"
            if r.margen_hoy is None
            else f"{r.margen_hoy * 100:.1f}% sobre venta".replace(".", ",")
        )
        if r.cumplimiento is None:
            self._v_meta.config(text="sin meta")
            self._d_meta.config(text="Configura la meta diaria")
        else:
            self._v_meta.config(text=f"{r.cumplimiento * 100:.0f}%")
            self._d_meta.config(
                text=("cumplida" if r.cumplimiento >= 1 else f"de {formatear_clp(r.meta)}")
            )
        self._tabla_resumen.delete(*self._tabla_resumen.get_children())
        for medio, (monto, cantidad) in r.por_medio.items():
            self._tabla_resumen.insert(
                "", "end", values=(NOMBRES_MEDIO[medio], formatear_clp(monto), cantidad)
            )
        self._tabla_ganancia.delete(*self._tabla_ganancia.get_children())
        for fila in r.mayor_ganancia:
            self._tabla_ganancia.insert(
                "", "end", values=(fila.nombre, formatear_clp(fila.ganancia))
            )
        self._tabla_avisos.delete(*self._tabla_avisos.get_children())
        self._destinos = {}
        for posicion, aviso in enumerate(r.avisos):
            self._destinos[str(posicion)] = aviso.destino
            self._tabla_avisos.insert(
                "",
                "end",
                iid=str(posicion),
                tags=("urgente",) if aviso.urgente else (),
                values=(aviso.titulo, aviso.detalle, "Ver →"),
            )
        self._lbl_resumen_dia.config(
            text=f"{r.transacciones} venta(s) hoy · total {formatear_clp(r.venta_hoy)}"
        )

    # ------------------------------------------------------------------ acciones --

    def _navegar(self, destino: str) -> None:
        if self._ir_a is not None:
            self._ir_a(destino)

    def _al_clic_en_aviso(self, evento: tk.Event) -> None:
        fila = self._tabla_avisos.identify_row(evento.y)
        if fila and self._tabla_avisos.identify_column(evento.x) == "#3":
            self._tabla_avisos.selection_set(fila)
            self._abrir_aviso()

    def _abrir_aviso(self) -> None:
        seleccion = self._tabla_avisos.selection()
        if seleccion:
            self._navegar(self._destinos.get(seleccion[0], ""))

    def guardar_metas(self, valores: dict[str, str]) -> bool:
        from pos.dominio.configuracion import validar_parametro

        nuevos = {}
        for clave, _titulo in TIPOS_DE_DIA:
            try:
                nuevos[clave] = validar_parametro(clave, valores[clave] or "0")
            except ErrorDominio as error:
                from tkinter import messagebox

                messagebox.showerror("Meta diaria", str(error))
                return False
        for clave, titulo in TIPOS_DE_DIA:
            antes = self._config.obtener(clave)
            if antes != nuevos[clave]:
                self._config.guardar(clave, nuevos[clave])
                if self._auditor is not None:
                    self._auditor.registrar(
                        "Cambio de meta diaria",
                        titulo,
                        formatear_clp(antes),
                        formatear_clp(nuevos[clave]),
                    )
        self.refrescar()
        return True

    def _dialogo_meta(self) -> tk.Toplevel:
        return pedir_formulario(
            self,
            "Meta diaria de venta",
            [
                (
                    clave,
                    f"{titulo} (CLP)",
                    formatear_clp(self._config.obtener(clave)).lstrip("$"),
                    None,
                )
                for clave, titulo in TIPOS_DE_DIA
            ],
            self.guardar_metas,
            "Guardar metas",
            nota="Sobre el monto vendido en el día. 0 = sin meta. "
            "Valores definidos por la Product Owner.",
        )
