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
from tkinter import messagebox, simpledialog, ttk

from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.aplicacion.casos_uso.editar_producto import EditarProducto  # NUEVO IMPORT
from pos.aplicacion.puertos import RepositorioProductos
from pos.dominio.errores import ErrorDominio
from pos.dominio.productos import UnidadVenta


class VentanaProductos(tk.Tk):
    def __init__(
        self,
        repositorio: RepositorioProductos,
        registrar_producto: RegistrarProducto,
        editar_producto: EditarProducto,  # NUEVO PARAMETRO
    ) -> None:
        super().__init__()
        self._repo = repositorio
        self._registrar = registrar_producto
        self._editar = editar_producto    # NUEVO ATRIBUTO
        
        self.title("NaturalSur - Productos")
        self.geometry("850x550") # Un poco mas ancha para que quepan los campos
        self._construir()
        self._refrescar()

    # NUEVO: Barra de Búsqueda (HU-PRD-07)
        marco_busqueda = ttk.Frame(self)
        marco_busqueda.pack(fill="x", padx=12, pady=4)
        
        ttk.Label(marco_busqueda, text="Buscar (Nombre/Código):").pack(side="left", padx=4)
        self._entrada_busqueda = ttk.Entry(marco_busqueda, width=30)
        self._entrada_busqueda.pack(side="left", padx=4)
        
        ttk.Button(marco_busqueda, text="Buscar", command=self._ejecutar_busqueda).pack(side="left", padx=4)
        ttk.Button(marco_busqueda, text="Limpiar", command=self._limpiar_busqueda).pack(side="left", padx=4)

    def _ejecutar_busqueda(self) -> None:
        termino = self._entrada_busqueda.get().strip()
        if not termino:
            self._refrescar()
            return
            
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
            
        resultados = self._repo.buscar(termino)
        for p in resultados:
            self._tabla.insert(
                "", "end", values=(p.codigo, p.nombre, p.precio.monto, p.unidad_venta.value, p.categoria_id)
            )

    def _limpiar_busqueda(self) -> None:
        self._entrada_busqueda.delete(0, tk.END)
        self._refrescar()

    def _construir(self) -> None:
        marco_form = ttk.LabelFrame(self, text="Nuevo producto")
        marco_form.pack(fill="x", padx=12, pady=8)

        # Variables reactivas para recálculo en vivo
        self._precio_var = tk.StringVar()
        self._costo_var = tk.StringVar()
        self._margen_var = tk.StringVar(value="Sin dato")
        self._markup_var = tk.StringVar(value="Sin dato")

        self._precio_var.trace_add("write", self._actualizar_indicadores)
        self._costo_var.trace_add("write", self._actualizar_indicadores)


        # Fila 1: Datos básicos
        self._entradas: dict[str, ttk.Entry] = {}
        
        ttk.Label(marco_form, text="Código").grid(row=0, column=0, padx=4, pady=6)
        self._entradas["codigo"] = ttk.Entry(marco_form, width=16)
        self._entradas["codigo"].grid(row=0, column=1, padx=4, pady=6)

        ttk.Label(marco_form, text="Nombre").grid(row=0, column=2, padx=4, pady=6)
        self._entradas["nombre"] = ttk.Entry(marco_form, width=16)
        self._entradas["nombre"].grid(row=0, column=3, padx=4, pady=6)

        ttk.Label(marco_form, text="Categoría ID").grid(row=0, column=4, padx=4, pady=6)
        self._categoria = ttk.Entry(marco_form, width=12)
        self._categoria.grid(row=0, column=5, padx=4, pady=6)

        # Fila 2: Precios, Costos e Indicadores derivados (HU-PRD-03 / HU-PRD-08)
        ttk.Label(marco_form, text="Costo (CLP)").grid(row=1, column=0, padx=4, pady=6)
        ttk.Entry(marco_form, textvariable=self._costo_var, width=16).grid(row=1, column=1, padx=4, pady=6)

        ttk.Label(marco_form, text="Precio (CLP)").grid(row=1, column=2, padx=4, pady=6)
        ttk.Entry(marco_form, textvariable=self._precio_var, width=16).grid(row=1, column=3, padx=4, pady=6)
        self._entradas["precio"] = ttk.Entry(marco_form, textvariable=self._precio_var, width=16) # Referencia interna

        ttk.Label(marco_form, text="Margen s/Venta").grid(row=1, column=4, padx=4, pady=6)
        ttk.Entry(marco_form, textvariable=self._margen_var, state="readonly", width=12).grid(row=1, column=5, padx=4, pady=6)

        ttk.Label(marco_form, text="Markup s/Costo").grid(row=1, column=6, padx=4, pady=6)
        ttk.Entry(marco_form, textvariable=self._markup_var, state="readonly", width=12).grid(row=1, column=7, padx=4, pady=6)

        ttk.Button(marco_form, text="Sugerir Precio", command=self._sugerir_precio).grid(row=1, column=8, padx=8)

        # Fila 3: Configuraciones específicas
        self._granel = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco_form, text="A granel", variable=self._granel).grid(row=2, column=0, columnspan=2, sticky="w", padx=4)

        self._perecible = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco_form, text="Perecible", variable=self._perecible).grid(row=2, column=2, sticky="w", padx=4)

        ttk.Label(marco_form, text="Días aviso (vencimiento):").grid(row=2, column=3, columnspan=2, sticky="e")
        self._dias_aviso = ttk.Entry(marco_form, width=6)
        self._dias_aviso.grid(row=2, column=5, sticky="w", padx=4)

        ttk.Button(marco_form, text="Agregar", command=self._agregar).grid(row=2, column=8, padx=4, pady=6, sticky="e")

        # Tabla de productos
        columnas = ("codigo", "nombre", "precio", "unidad", "categoria")
        self._tabla = ttk.Treeview(self, columns=columnas, show="headings")
        for col, titulo in zip(columnas, ("Codigo", "Nombre", "Precio", "Unidad", "Categoría"), strict=True):
            self._tabla.heading(col, text=titulo)
        self._tabla.pack(fill="both", expand=True, padx=12, pady=8)

    def _actualizar_indicadores(self, *args) -> None:
        costo_str = self._costo_var.get().strip()
        precio_str = self._precio_var.get().strip()

        if not costo_str:
            self._margen_var.set("Sin dato")
            self._markup_var.set("Sin dato")
            return

        try:
            costo = int(costo_str)
            precio = int(precio_str) if precio_str else 0
            
            if precio == 0:
                self._margen_var.set("0.0%")
                self._markup_var.set("0.0%")
                return

            margen = ((precio - costo) / precio) * 100
            markup = ((precio - costo) / costo) * 100 if costo > 0 else 100.0

            self._margen_var.set(f"{margen:.1f}%")
            self._markup_var.set(f"{markup:.1f}%")
        except ValueError:
            self._margen_var.set("Error")
            self._markup_var.set("Error")

    def _sugerir_precio(self) -> None:
        costo_str = self._costo_var.get().strip()
        if not costo_str:
            messagebox.showwarning("Atención", "Debe ingresar un costo primero para sugerir un precio.")
            return
            
        try:
            costo = int(costo_str)
            precio_sugerido = int(costo * 1.40) # Margen sugerido de ejemplo
            if messagebox.askyesno("Sugerencia", f"¿Aplicar precio sugerido de ${precio_sugerido}?"):
                self._precio_var.set(str(precio_sugerido))
        except ValueError:
            messagebox.showwarning("Atención", "El costo ingresado no es válido.")

    def _agregar(self) -> None:
        try:
            unidad = UnidadVenta.GRANEL if self._granel.get() else UnidadVenta.UNIDAD
            dias_str = self._dias_aviso.get().strip()
            dias = int(dias_str) if dias_str else None

            self._registrar.ejecutar(
                codigo=self._entradas["codigo"].get().strip(),
                nombre=self._entradas["nombre"].get().strip(),
                precio=int(self._entradas["precio"].get() or 0),
                categoria_id=self._categoria.get().strip(),
                unidad_venta=unidad,
                es_perecible=self._perecible.get(),
                dias_aviso_vencimiento=dias
            )
            self._refrescar()
            messagebox.showinfo("Éxito", "Producto registrado correctamente.")
        except (ErrorDominio, ValueError) as exc:
            messagebox.showerror("No se pudo agregar", str(exc))

    def _editar_seleccionado(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un producto de la tabla para editar.")
            return

        item = self._tabla.item(seleccion[0])
        codigo, nombre, precio_actual, unidad, categoria = item["values"]

        # Pedimos el nuevo precio con un dialogo simple de Tkinter
        nuevo_precio_str = simpledialog.askstring("Editar Precio", f"Nuevo precio para {nombre}:", initialvalue=str(precio_actual))
        
        if nuevo_precio_str is not None:
            try:
                self._editar.ejecutar(
                    codigo=str(codigo),
                    nuevo_nombre=str(nombre),
                    nuevo_precio=int(nuevo_precio_str),
                    nueva_categoria_id=str(categoria),
                    usuario="Eduardo_Caja1" # Usuario quemado por ahora para el test
                )
                self._refrescar()
                messagebox.showinfo("Éxito", "Producto actualizado (Historial registrado si el precio cambió).")
            except (ErrorDominio, ValueError) as exc:
                messagebox.showerror("Error al editar", str(exc))

    def _refrescar(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        for p in self._repo.listar():
            self._tabla.insert(
                "", "end", values=(p.codigo, p.nombre, p.precio.monto, p.unidad_venta.value, p.categoria_id)
            )