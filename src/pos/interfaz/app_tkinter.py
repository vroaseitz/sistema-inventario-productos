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
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.aplicacion.puertos import RepositorioProductos
from pos.dominio.errores import ErrorDominio
from pos.dominio.productos import UnidadVenta


class VentanaProductos(tk.Tk):
    def __init__(
        self,
        repositorio: RepositorioProductos,
        registrar_producto: RegistrarProducto,
    ) -> None:
        super().__init__()
        self._repo = repositorio
        self._registrar = registrar_producto
        self.title("NaturalSur - Productos")
        self.geometry("720x480")
        self._construir()
        self._refrescar()

    def _construir(self) -> None:
        marco_form = ttk.LabelFrame(self, text="Nuevo producto")
        marco_form.pack(fill="x", padx=12, pady=8)

        self._entradas: dict[str, ttk.Entry] = {}
        for i, (clave, etiqueta) in enumerate(
            [("codigo", "Codigo"), ("nombre", "Nombre"), ("precio", "Precio (CLP)")]
        ):
            ttk.Label(marco_form, text=etiqueta).grid(row=0, column=i * 2, padx=4, pady=6)
            entrada = ttk.Entry(marco_form, width=16)
            entrada.grid(row=0, column=i * 2 + 1, padx=4, pady=6)
            self._entradas[clave] = entrada

        self._granel = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco_form, text="A granel (por kg)", variable=self._granel).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=4
        )
        ttk.Button(marco_form, text="Agregar", command=self._agregar).grid(
            row=1, column=5, padx=4, pady=6, sticky="e"
        )

        columnas = ("codigo", "nombre", "precio", "unidad")
        self._tabla = ttk.Treeview(self, columns=columnas, show="headings")
        for col, titulo in zip(columnas, ("Codigo", "Nombre", "Precio", "Unidad"), strict=True):
            self._tabla.heading(col, text=titulo)
        self._tabla.pack(fill="both", expand=True, padx=12, pady=8)

    def _agregar(self) -> None:
        try:
            unidad = UnidadVenta.GRANEL if self._granel.get() else UnidadVenta.UNIDAD
            self._registrar.ejecutar(
                codigo=self._entradas["codigo"].get().strip(),
                nombre=self._entradas["nombre"].get().strip(),
                precio=int(self._entradas["precio"].get() or 0),
                unidad_venta=unidad,
            )
            self._refrescar()
        except (ErrorDominio, ValueError) as exc:
            messagebox.showerror("No se pudo agregar", str(exc))

    def _refrescar(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        for p in self._repo.listar():
            self._tabla.insert(
                "", "end", values=(p.codigo, p.nombre, p.precio.monto, p.unidad_venta.value)
            )
