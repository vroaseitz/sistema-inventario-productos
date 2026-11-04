"""Pantalla F6 Reportes: ventas (HU-REP-02), rentabilidad (HU-REP-03) y rotacion (HU-REP-04)."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.cambiar_estado_producto import CambiarEstadoProducto
from pos.aplicacion.casos_uso.reporte_rentabilidad import (
    ORDENES_RENTABILIDAD,
    ReporteRentabilidad,
    ReporteRotacion,
)
from pos.aplicacion.casos_uso.reporte_ventas import SIN_CATEGORIA, ReporteVentas
from pos.aplicacion.puertos import RepositorioCategorias
from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_cantidad
from pos.dominio.pagos import MedioPago
from pos.interfaz import tema
from pos.interfaz.campo_fecha import CampoFecha
from pos.interfaz.exportar import exportar_con_dialogo


def _clp(monto: int) -> str:
    return "$" + f"{monto:,}".replace(",", ".")


_NOMBRES_MEDIO = {
    MedioPago.EFECTIVO.value: "Efectivo",
    MedioPago.TARJETA.value: "Tarjeta",
    MedioPago.TRANSFERENCIA.value: "Transferencia",
    MedioPago.CREDITO_CLIENTE.value: "Crédito cliente",
}


def _nombre_medio(valor: str) -> str:
    return _NOMBRES_MEDIO.get(valor, valor.replace("_", " ").capitalize())


class VentanaReportes(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        reporte_ventas: ReporteVentas,
        repo_categorias: RepositorioCategorias | None = None,
        rentabilidad: ReporteRentabilidad | None = None,
        rotacion: ReporteRotacion | None = None,
        cambiar_estado: CambiarEstadoProducto | None = None,
    ) -> None:
        super().__init__(parent, padding=12)
        self._reporte = reporte_ventas
        self._rentabilidad = rentabilidad
        self._rotacion = rotacion
        self._cambiar_estado = cambiar_estado
        self._categorias = repo_categorias
        self._hoy_al_generar = date.today()
        # R-01: fechas con calendario desplegable (tambien se puede escribir AAAA-MM-DD).
        self._desde: CampoFecha
        self._hasta: CampoFecha
        self._resumen = tk.StringVar()

        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True)
        self._marco_ventas = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(self._marco_ventas, text="Ventas")
        filtros = ttk.LabelFrame(
            self._marco_ventas, text="Ventas por período y categoría", padding=10
        )
        filtros.pack(fill="x")
        self._desde = CampoFecha(filtros, date.today(), width=14)
        self._hasta = CampoFecha(filtros, date.today(), width=14)
        for columna, (texto, campo) in enumerate((("Desde", self._desde), ("Hasta", self._hasta))):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            campo.grid(row=1, column=columna, padx=4, sticky="w")
        tema.BotonAccion(
            filtros,
            "Generar",
            self.generar,
            "",
            "primario",
            color=tema.MODULOS_COLOR["F6"][0],
            fondo=tema.PAPEL,
        ).grid(row=1, column=2, padx=8)
        tema.BotonAccion(
            filtros,
            "Exportar",
            self.exportar_ventas,
            "F8",
            "normal",
            color=tema.MODULOS_COLOR["F6"][0],
            fondo=tema.PAPEL,
        ).grid(row=1, column=3, padx=4)
        ttk.Label(
            self._marco_ventas, textvariable=self._resumen, font=("TkDefaultFont", 11, "bold")
        ).pack(anchor="w", pady=8)

        self._por_categoria = self._tabla("Por categoría", ("Categoría", "Vendido"))
        self._por_medio = self._tabla("Por medio de pago", ("Medio", "Cobrado"))
        if rentabilidad is not None:
            self._construir_rentabilidad()
        if rotacion is not None:
            self._construir_rotacion()
        self.generar()

    def _nombre_categoria(self, categoria_id: int) -> str:
        if categoria_id == SIN_CATEGORIA:
            return "Sin categoría"
        nombre = self._categorias.nombre_de(categoria_id) if self._categorias else None
        return nombre or "Sin categoría"

    def al_mostrar(self) -> None:
        """R-02: el reporte se armaba solo al abrir la app y quedaba vacio; ahora se regenera.

        Si el dia cambio desde la ultima vez y las fechas seguian en «hoy», se actualizan.
        """
        hoy = date.today()
        if hoy != self._hoy_al_generar:
            for campo in (self._desde, self._hasta):
                if campo.get().strip() == self._hoy_al_generar.isoformat():
                    campo.set(hoy.isoformat())
            self._hoy_al_generar = hoy
        self.generar()
        self.generar_rentabilidad()
        self.generar_rotacion()

    def _tabla(self, titulo: str, columnas: tuple[str, str]) -> ttk.Treeview:
        ttk.Label(self._marco_ventas, text=titulo).pack(anchor="w")
        tabla = ttk.Treeview(self._marco_ventas, columns=columnas, show="headings", height=6)
        for columna in columnas:
            tabla.heading(columna, text=columna)
        tabla.pack(fill="x", pady=(0, 8))
        return tabla

    def generar(self) -> None:
        try:
            desde = datetime.strptime(self._desde.get().strip(), "%Y-%m-%d").date()
            hasta = datetime.strptime(self._hasta.get().strip(), "%Y-%m-%d").date()
            datos = self._reporte.ejecutar(desde, hasta)
        except ValueError as error:
            messagebox.showerror("Reportes", f"Revisa las fechas: {error}")
            return
        self._resumen.set(
            f"{datos.cantidad_ventas} {'venta' if datos.cantidad_ventas == 1 else 'ventas'}"
            f" · total {_clp(datos.total)} · "
            f"ticket promedio {_clp(datos.ticket_promedio)}"
        )
        for tabla, filas in (
            (
                self._por_categoria,
                [
                    (self._nombre_categoria(c), _clp(m))
                    for c, m in sorted(
                        datos.por_categoria.items(), key=lambda x: self._nombre_categoria(x[0])
                    )
                ],
            ),
            (
                self._por_medio,
                [(_nombre_medio(k), _clp(m)) for k, m in sorted(datos.por_medio_pago.items())],
            ),
        ):
            tabla.delete(*tabla.get_children())
            for fila in filas:
                tabla.insert("", "end", values=fila)

    # -------------------------------------------------------------- exportar ventas --

    def exportar_ventas(self) -> None:
        filas = [
            ("Categoría", *self._por_categoria.item(i, "values"))
            for i in self._por_categoria.get_children()
        ]
        filas += [
            ("Medio de pago", *self._por_medio.item(i, "values"))
            for i in self._por_medio.get_children()
        ]
        exportar_con_dialogo("ventas-por-periodo.csv", ("Tipo", "Detalle", "Monto"), filas)

    # --------------------------------------------------- rentabilidad (HU-REP-03) --

    def _categorias_para_filtro(self) -> dict[str, int | None]:
        opciones: dict[str, int | None] = {"Todas": None}
        if self._categorias is not None:
            for categoria in self._categorias.listar():
                opciones[categoria.nombre] = categoria.id
        return opciones

    def _construir_rentabilidad(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Rentabilidad")
        filtros = ttk.Frame(marco)
        filtros.pack(fill="x")
        self._r_desde = CampoFecha(filtros, date.today().replace(day=1), width=12)
        self._r_hasta = CampoFecha(filtros, date.today(), width=12)
        self._r_categoria = tk.StringVar(value="Todas")
        self._r_orden = tk.StringVar(value=ORDENES_RENTABILIDAD[0])
        for columna, (texto, widget) in enumerate(
            (
                ("Desde", self._r_desde),
                ("Hasta", self._r_hasta),
                (
                    "Categoría",
                    ttk.Combobox(
                        filtros,
                        textvariable=self._r_categoria,
                        values=list(self._categorias_para_filtro()),
                        state="readonly",
                        width=22,
                    ),
                ),
                (
                    "Ordenar",
                    ttk.Combobox(
                        filtros,
                        textvariable=self._r_orden,
                        values=list(ORDENES_RENTABILIDAD),
                        state="readonly",
                        width=16,
                    ),
                ),
            )
        ):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            widget.grid(row=1, column=columna, padx=4, sticky="w")
        tema.BotonAccion(
            filtros,
            "Generar",
            self.generar_rentabilidad,
            "",
            "primario",
            color=tema.MODULOS_COLOR["F6"][0],
            fondo=tema.PAPEL,
        ).grid(row=1, column=4, padx=8)
        tema.BotonAccion(
            filtros,
            "Exportar",
            self.exportar_rentabilidad,
            "F8",
            "normal",
            color=tema.MODULOS_COLOR["F6"][0],
            fondo=tema.PAPEL,
        ).grid(row=1, column=5, padx=4)
        columnas = ("producto", "unidades", "venta", "costo", "ganancia", "margen")
        self._tabla_rentab = ttk.Treeview(marco, columns=columnas, show="headings", height=8)
        for clave, titulo, ancho, ancla in (
            ("producto", "Producto", 280, "w"),
            ("unidades", "Unidades", 80, "e"),
            ("venta", "Venta neta", 110, "e"),
            ("costo", "Costo", 110, "e"),
            ("ganancia", "Ganancia", 120, "e"),
            ("margen", "Margen", 80, "e"),
        ):
            self._tabla_rentab.heading(clave, text=titulo)
            self._tabla_rentab.column(clave, width=ancho, anchor=ancla)
        self._tabla_rentab.tag_configure("sin_costo", foreground="#a11")
        # Lo de abajo se empaqueta primero: si la ventana es baja, la tabla cede espacio (no el
        # resumen ni la nota, que antes se recortaban).
        ttk.Label(
            marco,
            text="Usa el costo que tenía el producto cuando se vendió, no el de hoy, y la venta "
            "sin IVA. Un producto "
            "sin costo cargado no se supone en cero: se informa y queda fuera del margen.",
            foreground="#666",
            wraplength=760,
        ).pack(side="bottom", anchor="w", pady=(4, 0))
        self._lbl_rentab = ttk.Label(marco, text="", font=("TkDefaultFont", 11, "bold"))
        self._lbl_rentab.pack(side="bottom", anchor="w")
        self._tabla_rentab.pack(fill="both", expand=True, pady=8)

    def generar_rentabilidad(self) -> list:
        if self._rentabilidad is None:
            return []
        try:
            desde = datetime.strptime(self._r_desde.get().strip(), "%Y-%m-%d").date()
            hasta = datetime.strptime(self._r_hasta.get().strip(), "%Y-%m-%d").date()
            resumen = self._rentabilidad.ejecutar(
                desde,
                hasta,
                self._categorias_para_filtro().get(self._r_categoria.get()),
                self._r_orden.get(),
            )
        except ValueError as error:
            messagebox.showerror("Reportes", f"Revisa las fechas: {error}")
            return []
        self._tabla_rentab.delete(*self._tabla_rentab.get_children())
        for fila in resumen.filas:
            self._tabla_rentab.insert(
                "",
                "end",
                tags=("sin_costo",) if fila.sin_costo else (),
                values=(
                    fila.nombre,
                    "—" if fila.unidades is None else formatear_cantidad(fila.unidades),
                    _clp(fila.venta_neta),
                    "sin costo" if fila.sin_costo else _clp(fila.costo),
                    "no disponible" if fila.sin_costo else _clp(fila.ganancia),
                    "—" if fila.margen is None else f"{fila.margen * 100:.1f}%".replace(".", ","),
                ),
            )
        margen = resumen.margen_total
        self._lbl_rentab.config(
            text=f"Ganancia {_clp(resumen.ganancia_total)} "
            f"sobre {_clp(resumen.venta_neta_con_costo)} netos"
            + (f" (margen {margen * 100:.1f}%)".replace(".", ",") if margen is not None else "")
            + (
                f" · {_clp(resumen.venta_sin_costo)} vendidos sin costo, fuera del margen"
                if resumen.venta_sin_costo
                else ""
            )
        )
        return resumen.filas

    def exportar_rentabilidad(self) -> None:
        filas = [self._tabla_rentab.item(i, "values") for i in self._tabla_rentab.get_children()]
        exportar_con_dialogo(
            "rentabilidad.csv",
            ("Producto", "Unidades", "Venta neta", "Costo", "Ganancia", "Margen"),
            filas,
        )

    # ------------------------------------------------------- rotacion (HU-REP-04) --

    def _construir_rotacion(self) -> None:
        marco = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(marco, text="Rotación")
        filtros = ttk.Frame(marco)
        filtros.pack(fill="x")
        self._rot_dias = tk.StringVar(value="90 días")
        self._rot_categoria = tk.StringVar(value="Todas")
        self._rot_estado = tk.StringVar(value="Activos")
        for columna, (texto, variable, valores, ancho) in enumerate(
            (
                ("Sin venta en", self._rot_dias, ["30 días", "60 días", "90 días", "180 días"], 10),
                ("Categoría", self._rot_categoria, list(self._categorias_para_filtro()), 22),
                ("Estado", self._rot_estado, ["Activos", "Inactivos", "Todos"], 10),
            )
        ):
            ttk.Label(filtros, text=texto).grid(row=0, column=columna, sticky="w", padx=4)
            ttk.Combobox(
                filtros, textvariable=variable, values=valores, state="readonly", width=ancho
            ).grid(row=1, column=columna, padx=4, sticky="w")
        tema.BotonAccion(
            filtros,
            "Generar",
            self.generar_rotacion,
            "",
            "primario",
            color=tema.MODULOS_COLOR["F6"][0],
            fondo=tema.PAPEL,
        ).grid(row=1, column=3, padx=8)
        tema.BotonAccion(
            filtros,
            "Desactivar seleccionados",
            self._desactivar_seleccionados,
            "",
            "peligro",
            color=tema.MODULOS_COLOR["F6"][0],
            fondo=tema.PAPEL,
        ).grid(row=1, column=4, padx=4)
        tema.BotonAccion(
            filtros,
            "Exportar",
            self.exportar_rotacion,
            "F8",
            "normal",
            color=tema.MODULOS_COLOR["F6"][0],
            fondo=tema.PAPEL,
        ).grid(row=1, column=5, padx=4)
        columnas = ("producto", "ultima", "dias", "existencia", "estado")
        self._tabla_rotacion = ttk.Treeview(
            marco, columns=columnas, show="headings", height=14, selectmode="extended"
        )
        for clave, titulo, ancho, ancla in (
            ("producto", "Producto", 300, "w"),
            ("ultima", "Última venta", 110, "w"),
            ("dias", "Días detenido", 110, "e"),
            ("existencia", "Existencia", 90, "e"),
            ("estado", "Estado", 80, "w"),
        ):
            self._tabla_rotacion.heading(clave, text=titulo)
            self._tabla_rotacion.column(clave, width=ancho, anchor=ancla)
        self._tabla_rotacion.pack(fill="both", expand=True, pady=8)
        ttk.Label(
            marco,
            text="Es la medida que evita que el catálogo se llene de productos muertos. "
            "Desactivar saca el producto de la venta sin borrar su historial.",
            foreground="#666",
        ).pack(anchor="w")

    def generar_rotacion(self) -> list:
        if self._rotacion is None:
            return []
        dias = int(self._rot_dias.get().split()[0])
        filas = self._rotacion.ejecutar(
            dias,
            self._categorias_para_filtro().get(self._rot_categoria.get()),
            self._rot_estado.get(),
        )
        self._tabla_rotacion.delete(*self._tabla_rotacion.get_children())
        for fila in filas:
            self._tabla_rotacion.insert(
                "",
                "end",
                iid=fila.codigo,
                values=(
                    fila.nombre,
                    fila.ultima_venta.strftime("%d-%m-%Y") if fila.ultima_venta else "Nunca",
                    "—" if fila.dias_detenido is None else fila.dias_detenido,
                    formatear_cantidad(fila.existencia),
                    "Activo" if fila.activo else "Inactivo",
                ),
            )
        return filas

    def desactivar_productos(self, codigos: list[str]) -> int:
        """HU-PRD-06: desactiva los productos elegidos; devuelve cuantos."""
        if self._cambiar_estado is None:
            return 0
        hechos = 0
        for codigo in codigos:
            try:
                self._cambiar_estado.ejecutar(codigo, False)
                hechos += 1
            except ErrorDominio as error:
                messagebox.showerror("Rotación", str(error))
        self.generar_rotacion()
        return hechos

    def _desactivar_seleccionados(self) -> None:
        codigos = list(self._tabla_rotacion.selection())
        if not codigos:
            messagebox.showwarning("Rotación", "Elige uno o más productos de la lista")
            return
        if not messagebox.askyesno(
            "Desactivar productos",
            f"¿Desactivar {len(codigos)} producto(s)? Dejan de venderse; su historial se conserva.",
        ):
            return
        self.desactivar_productos(codigos)

    def exportar_rotacion(self) -> None:
        filas = [
            self._tabla_rotacion.item(i, "values") for i in self._tabla_rotacion.get_children()
        ]
        exportar_con_dialogo(
            "rotacion.csv",
            ("Producto", "Última venta", "Días detenido", "Existencia", "Estado"),
            filas,
        )
