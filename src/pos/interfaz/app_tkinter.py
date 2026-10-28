"""GUI de escritorio con Tkinter (incluida en CPython, corre en Windows 8.1).

Es un scaffold funcional y DESACOPLADO: la ventana recibe los casos de uso por
constructor y solo orquesta la vista. Toda la logica vive en dominio/aplicacion, por
eso los tests no dependen de la GUI. Ampliar hacia el POS completo (ventas, caja) se
hace agregando vistas que reusan los mismos casos de uso.

Se eligio Tkinter sobre PyQt5 por compatibilidad con Windows 8.1 sin dependencias
externas ni runtime de Qt/Visual C++. Ver docs/08-diseno/adr/0001.
"""

from __future__ import annotations

import tkinter as tk
import unicodedata
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.aplicacion.puertos import RepositorioProductos
from pos.dominio.errores import ErrorDominio
from pos.dominio.productos import CATEGORIAS_VALIDAS, Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero


def _normalizar(texto: str) -> str:
    """Quita tildes y pasa a minusculas para busqueda insensible (C-08b)."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sin_tildes.lower()


class VentanaProductos(tk.Tk):
    def __init__(
        self,
        repositorio: RepositorioProductos,
        registrar_producto: RegistrarProducto,
        editar_producto: EditarProducto,
    ) -> None:
        super().__init__()
        self._repo = repositorio
        self._registrar = registrar_producto
        self._editar = editar_producto

        self.title("NaturalSur - Productos")
        self.geometry("900x560")
        self._construir_busqueda()
        self._construir()
        self._refrescar()

    # --- Barra de busqueda (HU-PRD-07) -------------------------------------

    def _construir_busqueda(self) -> None:
        marco_busqueda = ttk.Frame(self)
        marco_busqueda.pack(fill="x", padx=12, pady=4)

        ttk.Label(marco_busqueda, text="Buscar (Nombre/Código):").pack(side="left", padx=4)
        self._entrada_busqueda = ttk.Entry(marco_busqueda, width=30)
        self._entrada_busqueda.pack(side="left", padx=4)

        ttk.Button(marco_busqueda, text="Buscar", command=self._ejecutar_busqueda).pack(
            side="left", padx=4
        )
        ttk.Button(marco_busqueda, text="Limpiar", command=self._limpiar_busqueda).pack(
            side="left", padx=4
        )

        # C-08a: la tecla Enter tambien dispara la busqueda.
        self._entrada_busqueda.bind("<Return>", lambda e: self._ejecutar_busqueda())

    def _ejecutar_busqueda(self) -> None:
        termino = _normalizar(self._entrada_busqueda.get().strip())
        if not termino:
            self._refrescar()
            return

        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

        # C-08b: normalizamos tanto la consulta como los nombres evaluados.
        resultados = [
            p
            for p in self._repo.listar()
            if termino in _normalizar(p.nombre) or termino in _normalizar(p.codigo)
        ]
        for p in resultados:
            self._insertar_fila(p)

    def _limpiar_busqueda(self) -> None:
        self._entrada_busqueda.delete(0, tk.END)
        self._refrescar()

    # --- Formulario ---------------------------------------------------------

    def _construir(self) -> None:
        marco_form = ttk.LabelFrame(self, text="Producto")
        marco_form.pack(fill="x", padx=12, pady=8)

        # Variables reactivas para recálculo en vivo
        self._precio_var = tk.StringVar()
        self._costo_var = tk.StringVar()
        self._margen_var = tk.StringVar(value="Sin dato")
        self._markup_var = tk.StringVar(value="Sin dato")

        self._precio_var.trace_add("write", self._actualizar_indicadores)
        self._costo_var.trace_add("write", self._actualizar_indicadores)

        self._entradas: dict[str, ttk.Entry] = {}
        self._producto_en_edicion: str | None = None

        # Fila 0: datos basicos
        ttk.Label(marco_form, text="Código").grid(row=0, column=0, padx=4, pady=6)
        self._entradas["codigo"] = ttk.Entry(marco_form, width=16)
        self._entradas["codigo"].grid(row=0, column=1, padx=4, pady=6)

        ttk.Label(marco_form, text="Nombre").grid(row=0, column=2, padx=4, pady=6)
        self._entradas["nombre"] = ttk.Entry(marco_form, width=16)
        self._entradas["nombre"].grid(row=0, column=3, padx=4, pady=6)

        ttk.Label(marco_form, text="Categoría").grid(row=0, column=4, padx=4, pady=6)
        # C-02 / C-04: categoria por lista desplegable, no texto libre.
        self._categoria = ttk.Combobox(
            marco_form,
            values=list(CATEGORIAS_VALIDAS),
            width=12,
            state="readonly",
        )
        self._categoria.grid(row=0, column=5, padx=4, pady=6)

        ttk.Label(marco_form, text="Costo (CLP)").grid(row=0, column=6, padx=4, pady=6)
        ttk.Entry(marco_form, textvariable=self._costo_var, width=12).grid(
            row=0, column=7, padx=4, pady=6
        )

        # Fila 1: precio e indicadores derivados (HU-PRD-03 / HU-PRD-08)
        ttk.Label(marco_form, text="Precio (CLP)").grid(row=1, column=0, padx=4, pady=6)
        self._entradas["precio"] = ttk.Entry(marco_form, textvariable=self._precio_var, width=16)
        self._entradas["precio"].grid(row=1, column=1, padx=4, pady=6)

        ttk.Label(marco_form, text="Margen s/Venta").grid(row=1, column=4, padx=4, pady=6)
        ttk.Entry(marco_form, textvariable=self._margen_var, state="readonly", width=12).grid(
            row=1, column=5, padx=4, pady=6
        )

        ttk.Label(marco_form, text="Markup s/Costo").grid(row=1, column=6, padx=4, pady=6)
        ttk.Entry(marco_form, textvariable=self._markup_var, state="readonly", width=12).grid(
            row=1, column=7, padx=4, pady=6
        )

        # Fila 2: configuraciones especificas
        self._granel = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco_form, text="A granel", variable=self._granel).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=4
        )

        # C-05: producto perecible requiere dias de aviso.
        self._perecible = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco_form, text="Perecible", variable=self._perecible).grid(
            row=2, column=2, sticky="w", padx=4
        )

        ttk.Label(marco_form, text="Días aviso:").grid(row=2, column=3, sticky="e")
        self._dias_aviso = ttk.Entry(marco_form, width=6)
        self._dias_aviso.grid(row=2, column=4, sticky="w", padx=4)

        ttk.Button(marco_form, text="Agregar", command=self._agregar).grid(
            row=2, column=7, padx=4, pady=6, sticky="e"
        )

        # Tabla de productos
        columnas = ("codigo", "nombre", "precio", "unidad", "categoria", "costo")
        self._tabla = ttk.Treeview(self, columns=columnas, show="headings")
        for col, titulo in zip(
            columnas,
            ("Codigo", "Nombre", "Precio", "Unidad", "Categoría", "Costo"),
            strict=True,
        ):
            self._tabla.heading(col, text=titulo)
        self._tabla.pack(fill="both", expand=True, padx=12, pady=8)

        # C-10: doble clic sobre la tabla abre la edicion.
        self._tabla.bind("<Double-1>", lambda e: self._editar_seleccionado())

        self._boton_guardar = ttk.Button(
            self, text="Agregar", command=self._guardar_desde_formulario
        )
        self._boton_guardar.pack(pady=(0, 8))

        self._entradas["codigo"].focus_set()

    # --- Indicadores derivados (C-06) ---------------------------------------

    def _actualizar_indicadores(self, *args) -> None:
        costo_str = self._costo_var.get().strip()
        precio_str = self._precio_var.get().strip()

        if not costo_str:
            self._margen_var.set("falta costo")
            self._markup_var.set("falta costo")
            return

        try:
            costo = int(costo_str)
            precio = int(precio_str) if precio_str else 0

            costo_vo = Costo(neto=Dinero(costo), iva=Dinero(0))
            producto = Producto(
                codigo="TEMP",
                nombre="TEMP",
                precio=Dinero(precio),
                categoria_id=1,
                costo=costo_vo,
            )

            margen = producto.margen
            self._margen_var.set(f"{margen * 100:.1f}%" if margen is not None else "Sin dato")

            # C-06: con costo 0 (o faltante) el markup no es calculable.
            markup = producto.markup
            if markup is not None:
                self._markup_var.set(f"{markup * 100:.1f}%")
            else:
                self._markup_var.set("falta costo")
        except (ValueError, ErrorDominio):
            self._margen_var.set("Sin dato")
            self._markup_var.set("Sin dato")

    # --- Altas ---------------------------------------------------------------

    def _agregar(self) -> None:
        try:
            unidad = UnidadVenta.GRANEL if self._granel.get() else UnidadVenta.UNIDAD
            cat_str = self._categoria.get().strip()
            if not cat_str:
                raise ValueError("La categoria es obligatoria (C-04).")
            cat_id = CATEGORIAS_VALIDAS.index(cat_str) + 1
            costo_str = self._costo_var.get().strip()
            costo_val = int(costo_str) if costo_str else None
            perecible = self._perecible.get()
            dias_str = self._dias_aviso.get().strip()
            dias_aviso = int(dias_str) if dias_str else None

            if perecible and dias_aviso is None:
                raise ValueError("Un producto perecible requiere dias de aviso (C-05a).")

            producto = self._registrar.ejecutar(
                codigo=self._entradas["codigo"].get().strip(),
                nombre=self._entradas["nombre"].get().strip(),
                precio=int(self._entradas["precio"].get() or 0),
                unidad_venta=unidad,
                categoria_id=cat_id,
                costo=costo_val,
                perecible=perecible,
                dias_aviso=dias_aviso,
            )
            self._refrescar()
            # C-11: limpiar todo el formulario y devolver el foco al codigo.
            self._limpiar_formulario()
            messagebox.showinfo("Éxito", f"Producto {producto.codigo} registrado correctamente.")
        except (ErrorDominio, ValueError) as exc:
            messagebox.showerror("No se pudo agregar", str(exc))

    def _limpiar_formulario(self) -> None:
        """C-11: deja el formulario en blanco y enfoca el campo codigo."""
        self._entradas["codigo"].delete(0, tk.END)
        self._entradas["nombre"].delete(0, tk.END)
        self._entradas["precio"].delete(0, tk.END)
        self._costo_var.set("")
        self._categoria.set("")
        self._granel.set(False)
        self._perecible.set(False)
        self._dias_aviso.delete(0, tk.END)
        self._margen_var.set("Sin dato")
        self._markup_var.set("Sin dato")
        self._entradas["codigo"].focus_set()

    # --- Edicion (C-10) -------------------------------------------------------

    def _editar_seleccionado(self) -> None:
        """Carga el producto seleccionado en el formulario para editarlo."""
        seleccion = self._tabla.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un producto de la tabla para editar.")
            return

        item = self._tabla.item(seleccion[0])
        codigo = str(item["values"][0])

        # C-10: leemos el producto REAL desde el repositorio.
        producto = self._repo.obtener_por_codigo(codigo)
        if producto is None:
            messagebox.showerror("Error al editar", "El producto no existe.")
            return

        # Rellenar todos los campos del formulario con los datos reales.
        self._entradas["codigo"].delete(0, tk.END)
        self._entradas["codigo"].insert(0, producto.codigo)
        self._entradas["codigo"].config(state="disabled")  # el codigo no se edita
        self._entradas["nombre"].delete(0, tk.END)
        self._entradas["nombre"].insert(0, producto.nombre)
        self._entradas["precio"].delete(0, tk.END)
        self._entradas["precio"].insert(0, str(producto.precio.monto))
        self._costo_var.set(str(producto.costo.neto.monto) if producto.costo else "")
        self._dias_aviso.delete(0, tk.END)
        if producto.dias_aviso is not None:
            self._dias_aviso.insert(0, str(producto.dias_aviso))
        self._granel.set(producto.es_granel)
        self._perecible.set(producto.perecible)
        if producto.categoria_id is not None and 1 <= producto.categoria_id <= len(
            CATEGORIAS_VALIDAS
        ):
            self._categoria.set(CATEGORIAS_VALIDAS[producto.categoria_id - 1])

        # Cambiar a modo edicion.
        self._producto_en_edicion = producto.codigo
        self._boton_guardar.config(text="Guardar cambios")
        self._entradas["nombre"].focus_set()

    def _guardar_desde_formulario(self) -> None:
        """Despacha a alta o edicion segun el modo actual del formulario."""
        if getattr(self, "_producto_en_edicion", None):
            self._confirmar_edicion()
        else:
            self._agregar()

    def _confirmar_edicion(self) -> None:
        """Aplica los cambios del formulario sobre el producto en edicion (C-10)."""
        codigo = self._producto_en_edicion
        try:
            cat_str = self._categoria.get().strip()
            if not cat_str:
                raise ValueError("La categoria es obligatoria (C-04).")
            cat_id = CATEGORIAS_VALIDAS.index(cat_str) + 1
            costo_str = self._costo_var.get().strip()
            costo_val = int(costo_str) if costo_str else None
            dias_str = self._dias_aviso.get().strip()
            dias_aviso = int(dias_str) if dias_str else None
            perecible = self._perecible.get()

            self._editar.ejecutar(
                codigo=codigo,
                nuevo_nombre=self._entradas["nombre"].get().strip(),
                nuevo_precio=int(self._entradas["precio"].get() or 0),
                nueva_categoria_id=cat_id,
                usuario="Usuario_POS",
                costo=costo_val,
                perecible=perecible,
                dias_aviso=dias_aviso if perecible else None,
            )
            self._salir_modo_edicion()
            self._refrescar()
            messagebox.showinfo(
                "Éxito", "Producto actualizado (Historial registrado si el precio cambió)."
            )
        except (ErrorDominio, ValueError) as exc:
            messagebox.showerror("Error al editar", str(exc))

    def _salir_modo_edicion(self) -> None:
        """Vuelve el formulario al modo alta y lo limpia (C-11)."""
        self._producto_en_edicion = None
        self._entradas["codigo"].config(state="normal")
        self._boton_guardar.config(text="Agregar")
        self._limpiar_formulario()

    # --- Tabla ----------------------------------------------------------------

    def _insertar_fila(self, p: Producto) -> None:
        self._tabla.insert(
            "",
            "end",
            values=(
                p.codigo,
                p.nombre,
                p.precio.monto,
                p.unidad_venta.value,
                p.categoria_id,
                p.costo.neto.monto if p.costo else "",
            ),
        )

    def _refrescar(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        for p in self._repo.listar():
            self._insertar_fila(p)
