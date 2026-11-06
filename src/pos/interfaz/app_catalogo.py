"""Pantalla F2 Catalogo con la forma del prototipo v3: Productos | Categorias.

Productos: barra de acciones, filtros (buscar, categoria, estado, costo), tabla con las filas
«Revisar» teñidas, ficha de producto (costo, precio, IVA, ganancia y markup en vivo) e historial
de precios. Categorias (CA-16): nueva, renombrar, fusionar y desactivar. Es un archivo aparte de
`app_tkinter.VentanaProductos` para no pisar el trabajo del otro desarrollador.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.cambiar_estado_producto import CambiarEstadoProducto
from pos.aplicacion.casos_uso.consultar_catalogo import ConsultarCatalogo, ConsultarCategorias
from pos.aplicacion.casos_uso.consultar_inventario import DefinirStockMinimo
from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.gestionar_categorias import GestionarCategorias
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.aplicacion.puertos import RepositorioCategorias, RepositorioHistorial, RepositorioProductos
from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_clp, parsear_monto
from pos.dominio.productos import UnidadVenta
from pos.dominio.value_objects import neto_de_precio
from pos.interfaz import tema
from pos.interfaz.combo_filtrable import ComboFiltrable
from pos.interfaz.dialogo_formulario import pedir_formulario
from pos.interfaz.exportar import exportar_con_dialogo

COLOR, CLARO = tema.MODULOS_COLOR["F2"]
TODAS = "Todas las categorías"
IVA = 19  # % de IVA chileno; solo informativo en la ficha


def _porcentaje(valor: float) -> str:
    return f"{valor * 100:.1f}%".replace(".", ",")


class VentanaCatalogo(ttk.Frame):
    """Marco del modulo F2; la ventana la aporta VentanaPrincipal."""

    def __init__(
        self,
        parent: tk.Misc,
        consultar: ConsultarCatalogo,
        consultar_categorias: ConsultarCategorias,
        registrar: RegistrarProducto,
        editar: EditarProducto,
        cambiar_estado: CambiarEstadoProducto,
        gestion_categorias: GestionarCategorias,
        definir_minimo: DefinirStockMinimo,
        repo_productos: RepositorioProductos,
        repo_categorias: RepositorioCategorias,
        repo_historial: RepositorioHistorial,
        sesion=None,
    ) -> None:
        super().__init__(parent)
        self._consultar = consultar
        self._consultar_categorias = consultar_categorias
        self._registrar = registrar
        self._editar = editar
        self._cambiar_estado = cambiar_estado
        self._gestion = gestion_categorias
        self._definir_minimo = definir_minimo
        self._repo = repo_productos
        self._repo_categorias = repo_categorias
        self._historial = repo_historial
        self._sesion = sesion
        self._buscar = tk.StringVar()
        self._categoria = tk.StringVar(value=TODAS)
        self._estado = tk.StringVar(value="Activos")
        self._costo = tk.StringVar(value="Todos")
        self._mensaje = tk.StringVar()
        self.ficha: tk.Toplevel | None = None

        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self._marco_productos = ttk.Frame(self._pestanas, padding=8)
        self._marco_categorias = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(self._marco_productos, text="Productos")
        self._pestanas.add(self._marco_categorias, text="Categorías")
        self._construir_productos()
        self._construir_categorias()
        tk.Label(self, textvariable=self._mensaje, fg=tema.MARCA, bg=tema.PAPEL, anchor="w").pack(
            fill="x", padx=14, pady=4
        )
        self.refrescar()

    # --------------------------------------------------------------- utilidades --

    def _usuario(self) -> str:
        return (self._sesion.nombre if self._sesion else "") or "Usuario_POS"

    def _categorias_activas(self) -> dict[str, int]:
        return {c.nombre: c.id for c in self._repo_categorias.listar(solo_activas=True)}

    def _tabla(self, padre: tk.Misc, columnas: tuple, altura: int = 14) -> ttk.Treeview:
        tabla = ttk.Treeview(
            padre, columns=[c[0] for c in columnas], show="headings", height=altura
        )
        for clave, titulo, ancho, ancla in columnas:
            tabla.heading(clave, text=titulo)
            tabla.column(clave, width=ancho, anchor=ancla)
        return tabla

    def _barra(self, padre: tk.Misc, botones: list[tuple]) -> tk.Frame:
        barra = tk.Frame(padre, bg=tema.PAPEL)
        for texto, comando, tecla, variante in botones:
            boton = tema.BotonAccion(
                barra, texto, comando, tecla, variante, color=COLOR, fondo=tema.PAPEL
            )
            boton.pack(side="left", padx=(0, 6))
        return barra

    # ----------------------------------------------------------------- productos --

    def _construir_productos(self) -> None:
        marco = self._marco_productos
        self._barra(
            marco,
            [
                ("Nuevo producto", self.nuevo, "INS", "primario"),
                ("Modificar", self.modificar, "↵", "normal"),
                ("Desactivar", self.alternar_estado, "DEL", "peligro"),
                ("Historial de precios", self.ver_historial, "", "normal"),
                ("Exportar", self.exportar, "F8", "normal"),
            ],
        ).pack(fill="x", pady=(0, 8))

        filtros = ttk.Frame(marco)
        filtros.pack(fill="x", pady=(0, 6))
        ttk.Label(filtros, text="Buscar (nombre o código)").grid(row=0, column=0, sticky="w")
        entrada = ttk.Entry(filtros, textvariable=self._buscar, width=34)
        entrada.grid(row=1, column=0, padx=(0, 10), sticky="w")
        entrada.bind("<KeyRelease>", lambda _e: self.refrescar())
        self._entrada_buscar = entrada
        for columna, (titulo, variable, valores, ancho) in enumerate(
            (
                ("Categoría", self._categoria, [TODAS], 26),
                ("Estado", self._estado, ["Activos", "Inactivos", "Todos"], 12),
                ("Costo", self._costo, ["Todos", "Con costo", "Sin costo"], 12),
            ),
            start=1,
        ):
            ttk.Label(filtros, text=titulo).grid(row=0, column=columna, sticky="w")
            if titulo == "Categoría":  # CA-18: se puede escribir para filtrar la lista
                combo = ComboFiltrable(filtros, variable, valores, ancho)
            else:
                combo = ttk.Combobox(
                    filtros, textvariable=variable, values=valores, state="readonly", width=ancho
                )
            combo.grid(row=1, column=columna, padx=(0, 10), sticky="w")
            combo.bind("<<ComboboxSelected>>", lambda _e: self.refrescar())
            if titulo == "Categoría":
                self._combo_categoria = combo
        ttk.Button(filtros, text="Limpiar", command=self.limpiar_filtros).grid(
            row=1, column=4, sticky="w"
        )

        columnas = (
            ("codigo", "Código", 130, "w"),
            ("nombre", "Nombre", 330, "w"),
            ("categoria", "Categoría", 190, "w"),
            ("precio", "Precio", 100, "e"),
            ("existencia", "Existencia", 100, "e"),
            ("estado", "Estado", 90, "center"),
        )
        self.tabla = self._tabla(marco, columnas)
        self.tabla.tag_configure("revisar", background=tema.ALERTA_FONDO)
        self.tabla.tag_configure("inactivo", foreground=tema.TINTA_3)
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<Double-1>", lambda _e: self.modificar())
        self.tabla.bind("<Return>", lambda _e: self.modificar())
        self.tabla.bind("<Delete>", lambda _e: self.alternar_estado())
        self._nota = tk.Label(marco, text="", anchor="w", bg=tema.PAPEL, fg=tema.TINTA_2)
        self._nota.pack(fill="x", pady=(4, 0))
        self.bind_all("<Insert>", self._atajo_nuevo, add="+")

    def _atajo_nuevo(self, _evento=None) -> None:
        if self.winfo_ismapped() and self._pestanas.index("current") == 0:
            self.nuevo()

    def limpiar_filtros(self) -> None:
        self._buscar.set("")
        self._categoria.set(TODAS)
        self._estado.set("Activos")
        self._costo.set("Todos")
        self.refrescar()

    def refrescar(self) -> None:
        nombres = self._categorias_activas()
        todas = {c.nombre: c.id for c in self._repo_categorias.listar()}
        self._combo_categoria.poner_opciones([TODAS, *todas])
        categoria_id = todas.get(self._categoria.get())
        filas = self._consultar.ejecutar(
            self._buscar.get(), categoria_id, self._estado.get(), self._costo.get()
        )
        seleccionado = self.codigo_seleccionado()
        self.tabla.delete(*self.tabla.get_children())
        revisar = 0
        for f in filas:
            etiquetas = ()
            if f.estado == "Revisar":
                etiquetas, revisar = ("revisar",), revisar + 1
            elif f.estado == "Inactivo":
                etiquetas = ("inactivo",)
            self.tabla.insert(
                "",
                "end",
                iid=f.codigo,
                values=(
                    f.codigo,
                    f.nombre,
                    f.categoria,
                    formatear_clp(f.precio) + ("/kg" if f.granel else ""),
                    f.existencia,
                    f.estado,
                ),
                tags=etiquetas,
            )
        if seleccionado and self.tabla.exists(seleccionado):
            self.tabla.selection_set(seleccionado)
        self._nota.config(
            text=f"{len(filas)} productos"
            + (f" · {revisar} para revisar (costo o precio dudoso)" if revisar else "")
        )
        del nombres
        self.refrescar_categorias()

    def codigo_seleccionado(self) -> str | None:
        seleccion = self.tabla.selection()
        return str(seleccion[0]) if seleccion else None

    def _exigir_seleccion(self) -> str | None:
        codigo = self.codigo_seleccionado()
        if codigo is None:
            messagebox.showwarning("Catálogo", "Elija primero un producto de la lista.")
        return codigo

    def nuevo(self) -> None:
        self._abrir_ficha(None)

    def modificar(self) -> None:
        codigo = self._exigir_seleccion()
        if codigo:
            self._abrir_ficha(codigo)

    def alternar_estado(self) -> None:
        codigo = self._exigir_seleccion()
        if not codigo:
            return
        producto = self._repo.obtener_por_codigo(codigo)
        if producto is None:
            return
        nuevo = not producto.activo
        if not nuevo and not messagebox.askyesno(
            "Desactivar producto",
            f"«{producto.nombre}» dejará de aparecer en la venta y en las listas.\n"
            "Su historial se conserva y se puede reactivar. ¿Desactivarlo?",
        ):
            return
        try:
            self._cambiar_estado.ejecutar(codigo, nuevo)
        except ErrorDominio as error:
            messagebox.showerror("Catálogo", str(error))
            return
        self._mensaje.set(f"{producto.nombre}: {'reactivado' if nuevo else 'desactivado'}.")
        self.refrescar()

    def exportar(self) -> None:
        filas = [self.tabla.item(i)["values"] for i in self.tabla.get_children()]
        exportar_con_dialogo(
            "catalogo.csv",
            ["Código", "Nombre", "Categoría", "Precio", "Existencia", "Estado"],
            filas,
        )

    # ------------------------------------------------------------ historial precios --

    def ver_historial(self, codigo: str | None = None) -> None:
        codigo = codigo or self._exigir_seleccion()
        if not codigo:
            return
        producto = self._repo.obtener_por_codigo(codigo)
        if producto is None:
            return
        ventana = tk.Toplevel(self)
        ventana.title(f"Historial de precios — {producto.nombre}")
        ventana.transient(self.winfo_toplevel())
        ttk.Label(
            ventana,
            text=f"{producto.nombre} ({codigo}) · precio actual "
            f"{formatear_clp(producto.precio.monto)}",
            font=tema.fuente(12, True),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        tabla = self._tabla(
            ventana,
            (
                ("fecha", "Fecha", 130, "w"),
                ("anterior", "Antes", 90, "e"),
                ("nuevo", "Ahora", 90, "e"),
                ("usuario", "Quién", 110, "w"),
                ("motivo", "Motivo", 260, "w"),
            ),
            altura=10,
        )
        tabla.pack(fill="both", expand=True, padx=12, pady=4)
        registros = self._historial.listar_por_producto(codigo)
        for r in registros:
            tabla.insert(
                "",
                "end",
                values=(
                    r.fecha.strftime("%d-%m-%Y %H:%M"),
                    formatear_clp(r.precio_anterior.monto),
                    formatear_clp(r.precio_nuevo.monto),
                    r.usuario,
                    r.motivo or "—",
                ),
            )
        if not registros:
            ttk.Label(ventana, text="Este producto aún no tiene cambios de precio.").pack(pady=4)
        ttk.Button(ventana, text="Cerrar", command=ventana.destroy).pack(pady=10)
        ventana.bind("<Escape>", lambda _e: ventana.destroy())
        self.historial_abierto = ventana
        ventana.grab_set()

    # ---------------------------------------------------------------------- ficha --

    def crear_producto(self, codigo: str, al_guardar: Callable[[str], None] | None = None) -> None:
        """CO-01: abre la ficha de un producto nuevo con el codigo ya escrito (desde otra
        pantalla, p. ej. la factura de compra). `al_guardar(codigo)` se llama al guardarla."""
        self._abrir_ficha(None, codigo_inicial=codigo, al_guardar=al_guardar)

    def _abrir_ficha(
        self,
        codigo: str | None,
        duplicar_de: str | None = None,
        codigo_inicial: str = "",
        al_guardar: Callable[[str], None] | None = None,
    ) -> None:
        """Ficha del producto: Producto · Costo · Precio y ganancia. `codigo` None = nuevo."""
        if self.ficha is not None and self.ficha.winfo_exists():
            self.ficha.destroy()
        base = self._repo.obtener_por_codigo(codigo or duplicar_de or "")
        editando = codigo is not None and base is not None
        ventana = tk.Toplevel(self)
        self.ficha = ventana
        ventana.title("Ficha de producto" if editando else "Nuevo producto")
        ventana.transient(self.winfo_toplevel())
        ventana.configure(bg=tema.PAPEL)
        categorias = self._categorias_activas()
        v = {
            "codigo": tk.StringVar(value="" if duplicar_de or not base else base.codigo),
            "nombre": tk.StringVar(value=base.nombre if base else ""),
            "categoria": tk.StringVar(value=""),
            "granel": tk.BooleanVar(value=bool(base and base.es_granel)),
            "costo": tk.StringVar(
                value=formatear_clp(base.costo.neto.monto).lstrip("$")
                if base and base.costo
                else ""
            ),
            "precio": tk.StringVar(
                value=formatear_clp(base.precio.monto).lstrip("$") if base else ""
            ),
            "perecible": tk.BooleanVar(value=bool(base and base.perecible)),
            "dias": tk.StringVar(value=str(base.dias_aviso) if base and base.dias_aviso else ""),
            "minimo": tk.StringVar(
                value=str(base.stock_minimo) if base and base.stock_minimo is not None else ""
            ),
            "motivo": tk.StringVar(),
            "iva": tk.StringVar(value="—"),
            "ganancia": tk.StringVar(value="—"),
            "margen": tk.StringVar(value="—"),
            "markup": tk.StringVar(value="—"),
        }
        if base:
            actual = self._repo_categorias.nombre_de(base.categoria_id)
            v["categoria"].set(actual or "")
            if actual and actual not in categorias:
                categorias[actual] = base.categoria_id  # categoria desactivada pero en uso
        ventana.v = v  # type: ignore[attr-defined]
        ventana.categorias = categorias  # type: ignore[attr-defined]
        ventana.codigo_original = base.codigo if editando and base else ""  # type: ignore[attr-defined]
        ventana.al_guardar = al_guardar  # type: ignore[attr-defined]
        if codigo_inicial and not editando:
            v["codigo"].set(codigo_inicial)  # CO-01: llega desde la factura de compra

        def seccion(titulo: str) -> ttk.LabelFrame:
            marco = ttk.LabelFrame(ventana, text=titulo, padding=8)
            marco.pack(fill="x", padx=12, pady=(8, 0))
            return marco

        def fila(marco, fila_n, etiqueta, widget):
            ttk.Label(marco, text=etiqueta).grid(row=fila_n, column=0, sticky="w", pady=3)
            widget.grid(row=fila_n, column=1, sticky="w", padx=8, pady=3)
            return widget

        a = seccion("Producto")
        fila(a, 0, "Código de barras", ttk.Entry(a, textvariable=v["codigo"], width=28))
        # CA-19: el código se puede cambiar (no puede repetirse y queda en la auditoría).
        fila(a, 1, "Nombre", ttk.Entry(a, textvariable=v["nombre"], width=44))
        fila(
            a,
            2,
            "Categoría",
            ComboFiltrable(a, v["categoria"], list(categorias), 30),
        )
        fila(
            a, 3, "", ttk.Checkbutton(a, text="Se vende a granel (por kilo)", variable=v["granel"])
        )
        fila(
            a,
            4,
            "",
            ttk.Checkbutton(a, text="Es perecible (tiene vencimiento)", variable=v["perecible"]),
        )
        fila(a, 5, "Avisar antes de vencer (días)", ttk.Entry(a, textvariable=v["dias"], width=8))
        fila(a, 6, "Existencia mínima (unidades)", ttk.Entry(a, textvariable=v["minimo"], width=8))

        b = seccion("Costo")
        fila(b, 0, "Costo neto ($)", ttk.Entry(b, textvariable=v["costo"], width=14))

        c = seccion("Precio y ganancia")
        fila(
            c,
            0,
            "Precio de venta ($, IVA incluido)",
            ttk.Entry(c, textvariable=v["precio"], width=14),
        )
        fila(c, 1, f"IVA {IVA} % incluido", ttk.Label(c, textvariable=v["iva"]))
        fila(c, 2, "Ganancia por unidad (sin IVA)", ttk.Label(c, textvariable=v["ganancia"]))
        fila(c, 3, "Margen (sobre el precio sin IVA)", ttk.Label(c, textvariable=v["margen"]))
        fila(c, 4, "Markup (sobre el costo)", ttk.Label(c, textvariable=v["markup"]))
        if editando:
            fila(
                c,
                5,
                "Motivo del cambio de precio",
                ttk.Entry(c, textvariable=v["motivo"], width=34),
            )

        for clave in ("costo", "precio"):
            v[clave].trace_add("write", lambda *_: self._recalcular(v))
        self._recalcular(v)

        botones = ttk.Frame(ventana)
        botones.pack(fill="x", padx=12, pady=12)
        ttk.Button(
            botones,
            text="Guardar",
            style="Primario.TButton",
            command=lambda: self._guardar_ficha(ventana, editando),
        ).pack(side="left")
        if editando:
            ttk.Button(
                botones,
                text="Historial de precios",
                command=lambda: self.ver_historial(base.codigo),
            ).pack(side="left", padx=6)
            ttk.Button(
                botones,
                text="Duplicar",
                command=lambda: (ventana.destroy(), self._abrir_ficha(None, base.codigo)),
            ).pack(side="left", padx=6)
            ttk.Button(
                botones,
                text="Reactivar" if not base.activo else "Desactivar",
                command=lambda: (ventana.destroy(), self._alternar_codigo(base.codigo)),
            ).pack(side="left", padx=6)
        ttk.Button(botones, text="Cancelar", command=ventana.destroy).pack(side="right")
        ventana.bind("<Escape>", lambda _e: ventana.destroy())
        ventana.grab_set()

    def _alternar_codigo(self, codigo: str) -> None:
        if self.tabla.exists(codigo):
            self.tabla.selection_set(codigo)
        self.alternar_estado()

    @staticmethod
    def _recalcular(v: dict) -> None:
        """IVA, ganancia, margen y markup en vivo; «falta costo» si no hay costo creíble."""
        try:
            precio = parsear_monto(v["precio"].get()) if v["precio"].get().strip() else None
        except ValueError:
            precio = None
        try:
            costo = parsear_monto(v["costo"].get()) if v["costo"].get().strip() else None
        except ValueError:
            costo = None
        if precio is None:
            for clave in ("iva", "ganancia", "margen", "markup"):
                v[clave].set("—")
            return
        # ADR 0004: el precio incluye IVA y el costo es neto; la ganancia se mide sin IVA.
        precio_neto = neto_de_precio(precio)
        v["iva"].set(formatear_clp(precio - precio_neto))
        if not costo:
            for clave in ("ganancia", "margen", "markup"):
                v[clave].set("falta costo")
            return
        ganancia = precio_neto - costo
        v["ganancia"].set(formatear_clp(ganancia))
        v["margen"].set(_porcentaje(ganancia / precio_neto) if precio_neto else "—")
        v["markup"].set(_porcentaje(ganancia / costo))

    def _guardar_ficha(self, ventana: tk.Toplevel, editando: bool) -> bool:
        """Valida, avisa si se vende bajo el costo, y registra o edita. True si quedó guardado."""
        v = ventana.v  # type: ignore[attr-defined]
        try:
            nombre_categoria = v["categoria"].get().strip()
            if not nombre_categoria:
                raise ValueError("La categoría es obligatoria.")
            categoria_id = ventana.categorias[nombre_categoria]  # type: ignore[attr-defined]
            costo_texto = v["costo"].get().strip()
            costo = parsear_monto(costo_texto) if costo_texto else None
            precio = parsear_monto(v["precio"].get() or "0")
            dias_texto = v["dias"].get().strip()
            dias = int(dias_texto) if dias_texto else None
            minimo_texto = v["minimo"].get().strip()
            minimo = int(minimo_texto) if minimo_texto else None
        except (ValueError, KeyError) as error:
            messagebox.showerror("No se pudo guardar", str(error) or "Revise los datos.")
            return False
        if (
            costo
            and precio < costo
            and not messagebox.askyesno(
                "Precio bajo el costo",
                f"El precio ({formatear_clp(precio)}) es menor que el costo "
                f"({formatear_clp(costo)}): "
                "se vendería con pérdida. ¿Guardar igual?",
            )
        ):
            return False
        codigo = v["codigo"].get().strip()
        granel = UnidadVenta.GRANEL if v["granel"].get() else UnidadVenta.UNIDAD
        try:
            if editando:
                original = ventana.codigo_original  # type: ignore[attr-defined]
                if codigo != original:
                    codigo = self._editar.cambiar_codigo(original, codigo)  # CA-19
                    ventana.codigo_original = codigo  # type: ignore[attr-defined]
                self._editar.ejecutar(
                    codigo,
                    v["nombre"].get().strip(),
                    precio,
                    categoria_id,
                    self._usuario(),
                    costo=costo,
                    perecible=v["perecible"].get(),
                    dias_aviso=dias,
                    motivo_precio=v["motivo"].get().strip(),
                )
            else:
                self._registrar.ejecutar(
                    codigo,
                    v["nombre"].get().strip(),
                    precio,
                    granel,
                    categoria_id,
                    costo,
                    v["perecible"].get(),
                    dias,
                )
            self._definir_minimo.ejecutar(codigo, None if granel is UnidadVenta.GRANEL else minimo)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo guardar", str(error))
            return False
        self._mensaje.set(
            f"Producto {codigo} {'actualizado' if editando else 'creado'} en «{nombre_categoria}»."
        )
        al_guardar = getattr(ventana, "al_guardar", None)
        ventana.destroy()
        self.refrescar()
        self.destacar_producto(codigo)  # queda elegido en la lista, con su categoría a la vista
        if callable(al_guardar):
            al_guardar(codigo)  # CO-01: vuelve a la pantalla que pidio crear el producto
        return True

    # ----------------------------------------------------------------- categorias --

    def _construir_categorias(self) -> None:
        marco = self._marco_categorias
        self._barra(
            marco,
            [
                ("Nueva categoría", self.nueva_categoria, "INS", "primario"),
                ("Renombrar", self.renombrar_categoria, "", "normal"),
                ("Fusionar", self.fusionar_categoria, "", "normal"),
                ("Desactivar / activar", self.alternar_categoria, "", "peligro"),
                ("Eliminar", self.eliminar_categoria, "", "peligro"),
            ],
        ).pack(fill="x", pady=(0, 8))
        self.tabla_categorias = self._tabla(
            marco,
            (
                ("nombre", "Categoría", 320, "w"),
                ("productos", "Productos", 100, "e"),
                ("venta", "Venta del mes", 140, "e"),
                ("participacion", "Participación", 120, "e"),
                ("estado", "Estado", 100, "center"),
            ),
        )
        self.tabla_categorias.tag_configure("inactiva", foreground=tema.TINTA_3)
        self.tabla_categorias.pack(fill="both", expand=True)

    def refrescar_categorias(self) -> None:
        seleccionada = self.categoria_seleccionada()
        self.tabla_categorias.delete(*self.tabla_categorias.get_children())
        for f in self._consultar_categorias.ejecutar():
            self.tabla_categorias.insert(
                "",
                "end",
                iid=str(f.id),
                values=(
                    f.nombre,
                    f.productos,
                    formatear_clp(f.venta_mes),
                    _porcentaje(f.participacion) if f.venta_mes else "—",
                    "Activa" if f.activa else "Inactiva",
                ),
                tags=() if f.activa else ("inactiva",),
            )
        if seleccionada is not None and self.tabla_categorias.exists(str(seleccionada)):
            self.tabla_categorias.selection_set(str(seleccionada))

    def destacar_categoria(self, categoria_id: int) -> None:
        """Elige la fila de la categoría y la trae a la vista (la lista puede ser larga)."""
        iid = str(categoria_id)
        if self.tabla_categorias.exists(iid):
            self.tabla_categorias.selection_set(iid)
            self.tabla_categorias.see(iid)

    def destacar_producto(self, codigo: str) -> None:
        if self.tabla.exists(codigo):
            self.tabla.selection_set(codigo)
            self.tabla.see(codigo)

    def categoria_seleccionada(self) -> int | None:
        seleccion = self.tabla_categorias.selection()
        return int(seleccion[0]) if seleccion else None

    def _exigir_categoria(self) -> int | None:
        categoria_id = self.categoria_seleccionada()
        if categoria_id is None:
            messagebox.showwarning("Categorías", "Elija primero una categoría de la lista.")
        return categoria_id

    def nueva_categoria(self) -> None:
        def aceptar(datos: dict[str, str]) -> bool:
            try:
                categoria = self._gestion.crear(datos["nombre"])
            except ErrorDominio as error:
                messagebox.showerror("Categorías", str(error))
                return False
            self._mensaje.set(
                f"Categoría «{categoria.nombre}» creada: ya está en la lista y en el selector."
            )
            self.refrescar()
            self.destacar_categoria(categoria.id)  # que se vea cuál es la nueva
            return True

        self.dialogo = pedir_formulario(
            self, "Nueva categoría", [("nombre", "Nombre", "", None)], aceptar, "Crear"
        )

    def renombrar_categoria(self) -> None:
        categoria_id = self._exigir_categoria()
        if categoria_id is None:
            return
        actual = self._repo_categorias.nombre_de(categoria_id) or ""

        def aceptar(datos: dict[str, str]) -> bool:
            try:
                self._gestion.renombrar(categoria_id, datos["nombre"])
            except ErrorDominio as error:
                messagebox.showerror("Categorías", str(error))
                return False
            self._mensaje.set(f"Categoría renombrada a «{datos['nombre'].strip()}».")
            self.refrescar()
            return True

        self.dialogo = pedir_formulario(
            self, "Renombrar categoría", [("nombre", "Nuevo nombre", actual, None)], aceptar
        )

    def fusionar_categoria(self) -> None:
        origen = self._exigir_categoria()
        if origen is None:
            return
        nombre_origen = self._repo_categorias.nombre_de(origen) or ""
        destinos = {
            c.nombre: c.id
            for c in self._repo_categorias.listar(solo_activas=True)
            if c.id != origen
        }

        def aceptar(datos: dict[str, str]) -> bool:
            destino = destinos.get(datos["destino"])
            if destino is None:
                messagebox.showerror("Categorías", "Elija la categoría que se queda.")
                return False
            try:
                movidos = self._gestion.fusionar(origen, destino)
            except ErrorDominio as error:
                messagebox.showerror("Categorías", str(error))
                return False
            self._mensaje.set(
                f"«{nombre_origen}» se fusionó en «{datos['destino']}»: "
                f"{movidos} productos movidos."
            )
            self.refrescar()
            return True

        self.dialogo = pedir_formulario(
            self,
            "Fusionar categorías",
            [("destino", "Se queda en", "", list(destinos))],
            aceptar,
            "Fusionar",
            nota=f"Todos los productos de «{nombre_origen}» pasan a la categoría elegida y "
            "«" + nombre_origen + "» se elimina.",
        )

    def eliminar_categoria(self) -> None:
        """CA-17: solo se elimina una categoria sin productos; si no, se pide fusionar."""
        categoria_id = self._exigir_categoria()
        if categoria_id is None:
            return
        categoria = self._repo_categorias.obtener(categoria_id)
        if categoria is None:
            return
        if not messagebox.askyesno(
            "Eliminar categoría",
            f"¿Eliminar la categoría «{categoria.nombre}»? No se puede deshacer.",
        ):
            return
        try:
            self._gestion.eliminar(categoria_id)
        except ErrorDominio as error:
            messagebox.showerror("Categorías", str(error))
            return
        self._mensaje.set(f"Categoría «{categoria.nombre}» eliminada.")
        self.refrescar()

    def alternar_categoria(self) -> None:
        categoria_id = self._exigir_categoria()
        if categoria_id is None:
            return
        categoria = self._repo_categorias.obtener(categoria_id)
        if categoria is None:
            return
        try:
            self._gestion.cambiar_estado(categoria_id, not categoria.activa)
        except ErrorDominio as error:
            messagebox.showerror("Categorías", str(error))
            return
        self._mensaje.set(
            f"Categoría «{categoria.nombre}» "
            f"{'activada' if not categoria.activa else 'desactivada'}."
        )
        self.refrescar()

    # --------------------------------------------------------------------- shell --

    def al_mostrar(self) -> None:
        self.refrescar()

    def seleccionar_pestana(self, nombre: str) -> None:
        self._pestanas.select(0 if nombre.lower().startswith("prod") else 1)
