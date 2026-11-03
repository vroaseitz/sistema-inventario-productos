"""F3 Inventario: existencias con stock minimo, inventario valorizado y movimientos.

HU-INV-05, HU-INV-07 y HU-INV-08 segun el prototipo v3. Cada pestana es un panel que se arma con
un caso de uso de consulta; los modulos de este archivo no tocan la base directamente.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.consultar_inventario import (
    MOSTRAR,
    ConsultarExistencias,
    ConsultarMovimientos,
    DefinirStockMinimo,
    ReporteInventario,
)
from pos.aplicacion.puertos import RepositorioCategorias
from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_cantidad, formatear_clp
from pos.dominio.inventario import ESTADO_AGOTADO, ESTADO_BAJO_MINIMO, TipoMovimiento
from pos.interfaz.campo_fecha import CampoFecha
from pos.interfaz.dialogo_formulario import pedir_formulario
from pos.interfaz.exportar import exportar_con_dialogo

TIPOS = {
    "Todos": None,
    "Entrada": TipoMovimiento.ENTRADA,
    "Venta": TipoMovimiento.VENTA,
    "Merma": TipoMovimiento.MERMA,
    "Ajuste": TipoMovimiento.AJUSTE,
}


def _cantidad(valor: Decimal) -> str:
    return formatear_cantidad(valor)


def _opciones_categoria(repo: RepositorioCategorias | None) -> dict[str, int | None]:
    opciones: dict[str, int | None] = {"Todas": None}
    if repo is not None:
        for categoria in repo.listar():
            opciones[categoria.nombre] = categoria.id
    return opciones


def _tabla(padre: tk.Misc, columnas: tuple, altura: int = 14) -> ttk.Treeview:
    tabla = ttk.Treeview(padre, columns=[c[0] for c in columnas], show="headings", height=altura)
    for clave, titulo, ancho, ancla in columnas:
        tabla.heading(clave, text=titulo)
        tabla.column(clave, width=ancho, anchor=ancla)
    tabla.tag_configure("alerta", foreground="#a11")
    return tabla


class PanelExistencias(ttk.Frame):
    """Existencias por producto, con el minimo y el estado (HU-INV-05)."""

    def __init__(
        self,
        parent: tk.Misc,
        consultar: ConsultarExistencias,
        definir_minimo: DefinirStockMinimo,
        repo_categorias: RepositorioCategorias | None = None,
    ) -> None:
        super().__init__(parent, padding=8)
        self._consultar = consultar
        self._definir = definir_minimo
        self._categorias = _opciones_categoria(repo_categorias)
        self._buscar = tk.StringVar()
        self._categoria = tk.StringVar(value="Todas")
        self._mostrar = tk.StringVar(value="Todos")
        self._orden = tk.StringVar(value="Por urgencia")
        self._mensaje = tk.StringVar()

        filtros = ttk.Frame(self)
        filtros.pack(fill="x")
        entrada = ttk.Entry(filtros, textvariable=self._buscar, width=24)
        entrada.bind("<KeyRelease>", lambda _e: self.refrescar())
        combos = []
        for columna, (texto, widget) in enumerate(
            (
                ("Buscar", entrada),
                ("Categoría", self._combo(filtros, self._categoria, list(self._categorias), 22)),
                ("Mostrar", self._combo(filtros, self._mostrar, list(MOSTRAR), 14)),
                ("Ordenar", self._combo(filtros, self._orden, ["Por urgencia", "Nombre"], 14)),
            )
        ):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            widget.grid(row=1, column=columna, padx=4, sticky="w")
            combos.append(widget)
        ttk.Button(filtros, text="Definir mínimo", command=self._dialogo_minimo).grid(
            row=1, column=4, padx=8
        )
        ttk.Button(filtros, text="Exportar", command=self.exportar).grid(row=1, column=5, padx=4)
        self._tabla = _tabla(
            self,
            (
                ("producto", "Producto", 300, "w"),
                ("existencia", "Existencia", 100, "e"),
                ("minimo", "Mínimo", 80, "e"),
                ("ultima", "Última venta", 110, "w"),
                ("estado", "Estado", 120, "w"),
            ),
        )
        self._tabla.pack(fill="both", expand=True, pady=8)
        ttk.Label(self, textvariable=self._mensaje, foreground="#5B3E7E").pack(anchor="w")
        ttk.Label(
            self,
            text="El granel se muestra en kilos y no lleva mínimo. Un producto está «bajo el "
            "mínimo» cuando tiene menos unidades que su mínimo.",
            foreground="#666",
        ).pack(anchor="w")
        self.refrescar()

    def _combo(self, padre: tk.Misc, variable: tk.StringVar, valores: list[str], ancho: int):
        combo = ttk.Combobox(
            padre, textvariable=variable, values=valores, state="readonly", width=ancho
        )
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refrescar())
        return combo

    def consultar(self) -> list:
        return self._consultar.ejecutar(
            self._buscar.get().strip(),
            self._categorias.get(self._categoria.get()),
            self._mostrar.get(),
            self._orden.get(),
        )

    def refrescar(self) -> None:
        self._tabla.delete(*self._tabla.get_children())
        for fila in self.consultar():
            alerta = fila.estado in (ESTADO_AGOTADO, ESTADO_BAJO_MINIMO)
            self._tabla.insert(
                "",
                "end",
                iid=fila.codigo,
                tags=("alerta",) if alerta else (),
                values=(
                    fila.nombre,
                    f"{_cantidad(fila.existencia)} kg"
                    if fila.granel
                    else _cantidad(fila.existencia),
                    "—" if fila.minimo is None else fila.minimo,
                    fila.ultima_venta.strftime("%d-%m-%Y") if fila.ultima_venta else "—",
                    fila.estado,
                ),
            )

    def definir_minimo(self, codigo: str, texto: str) -> bool:
        """Guarda el minimo escrito; vacio lo quita."""
        texto = texto.strip()
        try:
            minimo = int(texto) if texto else None
        except ValueError:
            messagebox.showerror("Inventario", "El mínimo debe ser un número entero, por ejemplo 6")
            return False
        try:
            self._definir.ejecutar(codigo, minimo)
        except ErrorDominio as error:
            messagebox.showerror("Inventario", str(error))
            return False
        self._mensaje.set(f"Mínimo de {codigo} guardado")
        self.refrescar()
        return True

    def _dialogo_minimo(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            messagebox.showwarning("Inventario", "Elige un producto de la lista")
            return
        codigo = seleccion[0]
        actual = self._tabla.item(codigo, "values")[2]
        pedir_formulario(
            self,
            f"Stock mínimo de {self._tabla.item(codigo, 'values')[0]}",
            [
                (
                    "minimo",
                    "Mínimo (unidades; vacío = sin mínimo)",
                    "" if actual == "—" else str(actual),
                    None,
                )
            ],
            lambda v: self.definir_minimo(codigo, v["minimo"]),
            "Guardar mínimo",
        )

    def exportar(self) -> None:
        filas = [self._tabla.item(i, "values") for i in self._tabla.get_children()]
        exportar_con_dialogo(
            "existencias.csv", ("Producto", "Existencia", "Mínimo", "Última venta", "Estado"), filas
        )


class PanelReporteInventario(ttk.Frame):
    """Inventario valorizado a costo o a precio de venta (HU-INV-07)."""

    def __init__(
        self,
        parent: tk.Misc,
        reporte: ReporteInventario,
        repo_categorias: RepositorioCategorias | None = None,
    ) -> None:
        super().__init__(parent, padding=8)
        self._reporte = reporte
        self._categorias = _opciones_categoria(repo_categorias)
        self._categoria = tk.StringVar(value="Todas")
        self._incluir = tk.StringVar(value="Solo activos")
        self._valorizar = tk.StringVar(value="Costo")
        filtros = ttk.Frame(self)
        filtros.pack(fill="x")
        for columna, (texto, variable, valores, ancho) in enumerate(
            (
                ("Categoría", self._categoria, list(self._categorias), 22),
                ("Incluir", self._incluir, ["Solo activos", "Todos"], 14),
                ("Valorizar a", self._valorizar, ["Costo", "Precio de venta"], 16),
            )
        ):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            combo = ttk.Combobox(
                filtros, textvariable=variable, values=valores, state="readonly", width=ancho
            )
            combo.grid(row=1, column=columna, padx=4, sticky="w")
            combo.bind("<<ComboboxSelected>>", lambda _e: self.refrescar())
        ttk.Button(filtros, text="Exportar", command=self.exportar).grid(row=1, column=3, padx=8)
        self._tabla = _tabla(
            self,
            (
                ("producto", "Producto", 300, "w"),
                ("existencia", "Existencia", 100, "e"),
                ("unitario", "Valor unitario", 110, "e"),
                ("valor", "Valor en existencia", 140, "e"),
                ("estado", "Estado", 120, "w"),
            ),
        )
        self._tabla.pack(fill="both", expand=True, pady=8)
        self._lbl_total = ttk.Label(self, text="", font=("TkDefaultFont", 11, "bold"))
        self._lbl_total.pack(anchor="e")
        ttk.Label(
            self,
            text="Los productos a granel no se valorizan (decisión del levantamiento) y los que "
            "tienen el costo pendiente quedan fuera del total: valorizarlos en cero daría una "
            "cifra falsa.",
            foreground="#666",
            wraplength=760,
        ).pack(anchor="w")
        self.refrescar()

    def refrescar(self) -> None:
        resumen = self._reporte.ejecutar(
            self._categorias.get(self._categoria.get()), self._incluir.get(), self._valorizar.get()
        )
        self._tabla.delete(*self._tabla.get_children())
        for fila in resumen.filas:
            self._tabla.insert(
                "",
                "end",
                tags=("alerta",) if fila.exclusion else (),
                values=(
                    fila.nombre,
                    _cantidad(fila.existencia),
                    "—" if fila.unitario is None else formatear_clp(fila.unitario),
                    fila.exclusion if fila.exclusion else formatear_clp(fila.valor),
                    fila.estado,
                ),
            )
        sin = len([f for f in resumen.filas if f.exclusion])
        self._lbl_total.config(
            text=f"Total valorizado: {formatear_clp(resumen.total)}"
            + (f"  ·  {sin} producto(s) fuera del total" if sin else "")
        )

    def exportar(self) -> None:
        filas = [self._tabla.item(i, "values") for i in self._tabla.get_children()]
        exportar_con_dialogo(
            "inventario-valorizado.csv",
            ("Producto", "Existencia", "Valor unitario", "Valor en existencia", "Estado"),
            filas,
        )


class PanelMovimientos(ttk.Frame):
    """Historial de entradas, ventas, mermas y ajustes (HU-INV-08)."""

    def __init__(self, parent: tk.Misc, consultar: ConsultarMovimientos) -> None:
        super().__init__(parent, padding=8)
        self._consultar = consultar
        self._tipo = tk.StringVar(value="Todos")
        self._codigo = tk.StringVar()
        filtros = ttk.Frame(self)
        filtros.pack(fill="x")
        self._desde = CampoFecha(filtros, date.today() - timedelta(days=30), width=12)
        self._hasta = CampoFecha(filtros, date.today(), width=12)
        tipo = ttk.Combobox(
            filtros, textvariable=self._tipo, values=list(TIPOS), state="readonly", width=12
        )
        for columna, (texto, widget) in enumerate(
            (
                ("Desde", self._desde),
                ("Hasta", self._hasta),
                ("Movimiento", tipo),
                ("Código de producto", ttk.Entry(filtros, textvariable=self._codigo, width=16)),
            )
        ):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            widget.grid(row=1, column=columna, padx=4, sticky="w")
        ttk.Button(filtros, text="Buscar", command=self.refrescar).grid(row=1, column=4, padx=8)
        ttk.Button(filtros, text="Exportar", command=self.exportar).grid(row=1, column=5, padx=4)
        self._tabla = _tabla(
            self,
            (
                ("fecha", "Fecha", 120, "w"),
                ("producto", "Producto", 240, "w"),
                ("movimiento", "Movimiento", 90, "w"),
                ("cantidad", "Cantidad", 80, "e"),
                ("motivo", "Motivo", 180, "w"),
                ("usuario", "Usuario", 100, "w"),
            ),
        )
        self._tabla.pack(fill="both", expand=True, pady=8)
        ttk.Label(
            self,
            text="Cada línea dice de dónde salió o entró la mercadería. Un movimiento no se edita: "
            "un error se corrige con otro movimiento. Parte desde que se activó este historial.",
            foreground="#666",
            wraplength=760,
        ).pack(anchor="w")
        self.refrescar()

    def consultar(self) -> list:
        try:
            desde = datetime.strptime(self._desde.get().strip(), "%Y-%m-%d").date()
            hasta = datetime.strptime(self._hasta.get().strip(), "%Y-%m-%d").date()
            return self._consultar.ejecutar(
                desde, hasta, TIPOS[self._tipo.get()], self._codigo.get().strip() or None
            )
        except ValueError as error:
            messagebox.showerror("Inventario", f"Revisa las fechas: {error}")
            return []

    def refrescar(self) -> None:
        self._tabla.delete(*self._tabla.get_children())
        for movimiento, nombre in self.consultar():
            signo = "+" if movimiento.cantidad > 0 else "−"
            self._tabla.insert(
                "",
                "end",
                values=(
                    movimiento.fecha.strftime("%d-%m-%Y %H:%M"),
                    nombre,
                    movimiento.tipo.value.capitalize(),
                    f"{signo}{_cantidad(abs(movimiento.cantidad))}",
                    movimiento.motivo,
                    movimiento.usuario,
                ),
            )

    def exportar(self) -> None:
        filas = [self._tabla.item(i, "values") for i in self._tabla.get_children()]
        exportar_con_dialogo(
            "movimientos-de-inventario.csv",
            ("Fecha", "Producto", "Movimiento", "Cantidad", "Motivo", "Usuario"),
            filas,
        )
