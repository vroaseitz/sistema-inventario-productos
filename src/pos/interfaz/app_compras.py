"""Pantalla F5 Compras: registrar una factura de proveedor y ver las registradas.

Cubre HU-CMP-01 (factura de compra) y HU-CMP-02 (el detalle actualiza el costo y crea el lote).
Los proveedores (HU-CMP-03) son deseables y no comprometidos: por ahora el proveedor se escribe
o se elige entre los de facturas anteriores. Los gastos generales del local quedan fuera.
"""

from __future__ import annotations

import re
import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from pos.aplicacion.casos_uso.gestionar_proveedores import GestionarProveedores
from pos.aplicacion.casos_uso.registrar_factura_compra import RegistrarFacturaCompra
from pos.aplicacion.puertos import RepositorioFacturasCompra, RepositorioProductos
from pos.dominio.compras import FacturaCompra, LineaFactura, iva_de
from pos.dominio.errores import ErrorDominio
from pos.dominio.formato import formatear_cantidad, formatear_clp, parsear_monto
from pos.dominio.productos import UnidadVenta
from pos.interfaz import tema
from pos.interfaz.campo_fecha import CampoFecha
from pos.interfaz.dialogo_formulario import pedir_formulario


class VentanaCompras(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        registrar: RegistrarFacturaCompra,
        repo_facturas: RepositorioFacturasCompra,
        repo_productos: RepositorioProductos,
        gestion_proveedores: GestionarProveedores | None = None,
    ) -> None:
        super().__init__(parent)
        self._gestion_proveedores = gestion_proveedores
        self._registrar = registrar
        self._facturas = repo_facturas
        self._productos = repo_productos
        self._lineas: list[LineaFactura] = []
        self._neto_manual = False
        self._impuestos_manual = False
        self._actualizando = False
        self._avisando = False

        self._numero = tk.StringVar()
        self._neto = tk.StringVar()
        self._impuestos = tk.StringVar()
        self._total = tk.StringVar(value="Total: $0")
        self._suma = tk.StringVar(value="Suma del detalle: $0")
        self._diferencia = tk.StringVar(value="Diferencia con el neto: $0")
        self._mensaje = tk.StringVar()
        self._l_codigo = tk.StringVar()
        self._l_cantidad = tk.StringVar()
        self._l_costo = tk.StringVar()
        self._l_lote = tk.StringVar()

        color = tema.MODULOS_COLOR["F5"][0]
        barra = tk.Frame(self, bg=tema.PAPEL)
        barra.pack(fill="x", padx=12, pady=(8, 4))
        for texto, comando, tecla, variante in (
            ("Registrar factura", self.ir_a_registrar, "INS", "normal"),
            *(
                [
                    ("Nuevo proveedor", self.nuevo_proveedor, "", "normal"),
                    ("Editar proveedor", self.editar_proveedor, "", "normal"),
                ]
                if gestion_proveedores is not None
                else []
            ),
            # CO-04: confirmar es la accion principal: sin ella la factura no se guarda.
            ("Confirmar factura", lambda: self._confirmar(), "Ctrl+↵", "primario"),
            ("Limpiar", lambda: self._limpiar(), "", "normal"),
        ):
            tema.BotonAccion(
                barra, texto, comando, tecla, variante, color=color, fondo=tema.PAPEL
            ).pack(side="left", padx=(0, 6))
        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._tab_facturas = ttk.Frame(self._pestanas, padding=8)
        self._tab_registrar = ttk.Frame(self._pestanas, padding=8)
        self._tab_proveedores = ttk.Frame(self._pestanas, padding=8)
        self._pestanas.add(self._tab_facturas, text="Facturas de compra")
        self._pestanas.add(self._tab_registrar, text="Registrar factura")
        self._pestanas.add(self._tab_proveedores, text="Proveedores")
        self._pestana_actual = self._pestanas.select()
        # CO-04: avisa si se deja una factura a medio hacer.
        self._pestanas.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

        # --- Datos de la factura -----------------------------------------------------------
        datos = ttk.LabelFrame(self._tab_registrar, text="Registrar factura de compra", padding=10)
        datos.pack(fill="x")
        ttk.Label(datos, text="Proveedor").grid(row=0, column=0, sticky="w", padx=4)
        self._proveedor = ttk.Combobox(datos, width=28, values=self._nombres_proveedores())
        self._proveedor.grid(row=1, column=0, padx=4, pady=(2, 0), sticky="w")
        ttk.Label(datos, text="Número de documento").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Entry(datos, textvariable=self._numero, width=16).grid(
            row=1, column=1, padx=4, pady=(2, 0), sticky="w"
        )
        ttk.Label(datos, text="Fecha").grid(row=0, column=2, sticky="w", padx=4)
        self._fecha = CampoFecha(datos, date.today(), width=14)
        self._fecha.grid(row=1, column=2, padx=4, pady=(2, 0), sticky="w")
        ttk.Label(datos, text="Monto neto").grid(row=0, column=3, sticky="w", padx=4)
        entrada_neto = ttk.Entry(datos, textvariable=self._neto, width=14)
        entrada_neto.grid(row=1, column=3, padx=4, pady=(2, 0), sticky="w")
        ttk.Label(datos, text="Impuestos (IVA 19 %)").grid(row=0, column=4, sticky="w", padx=4)
        entrada_imp = ttk.Entry(datos, textvariable=self._impuestos, width=14)
        entrada_imp.grid(row=1, column=4, padx=4, pady=(2, 0), sticky="w")
        ttk.Label(datos, textvariable=self._total, font=("TkDefaultFont", 11, "bold")).grid(
            row=1, column=5, padx=12
        )
        entrada_neto.bind("<KeyRelease>", self._al_editar_neto)
        entrada_imp.bind("<KeyRelease>", self._al_editar_impuestos)

        # --- Agregar linea -----------------------------------------------------------------
        linea = ttk.LabelFrame(
            self._tab_registrar, text="Detalle de productos adquiridos", padding=10
        )
        linea.pack(fill="x", pady=(8, 0))
        self._l_vence = CampoFecha(linea, width=14)
        campos = (
            ("Código de producto", ttk.Entry(linea, textvariable=self._l_codigo, width=18)),
            ("Cantidad", ttk.Entry(linea, textvariable=self._l_cantidad, width=10)),
            ("Costo unitario neto", ttk.Entry(linea, textvariable=self._l_costo, width=14)),
            ("Vence (si es perecible)", self._l_vence),
            ("Código de lote (impreso)", ttk.Entry(linea, textvariable=self._l_lote, width=16)),
        )
        for columna, (titulo, widget) in enumerate(campos):
            etiqueta = ttk.Label(linea, text=titulo)
            etiqueta.grid(row=0, column=columna, sticky="w", padx=4)
            if titulo == "Cantidad":
                self._lbl_cantidad = etiqueta
            widget.grid(row=1, column=columna, padx=4, pady=(2, 0), sticky="w")
            if isinstance(widget, ttk.Entry):
                widget.bind("<Return>", lambda _e: self._agregar_linea())
        self._l_codigo.trace_add("write", self._actualizar_unidad)  # CO-05
        ttk.Button(linea, text="Agregar línea", command=self._agregar_linea).grid(
            row=1, column=len(campos), padx=8
        )
        ttk.Button(linea, text="Quitar línea", command=self._quitar_linea).grid(
            row=1, column=len(campos) + 1, padx=4
        )

        columnas = ("producto", "cantidad", "costo", "subtotal", "anterior")
        self._tabla = ttk.Treeview(self._tab_registrar, columns=columnas, show="headings", height=6)
        for clave, titulo, ancho, ancla in (
            ("producto", "Producto", 280, "w"),
            ("cantidad", "Cantidad", 80, "e"),
            ("costo", "Costo unitario neto", 140, "e"),
            ("subtotal", "Subtotal", 110, "e"),
            ("anterior", "Costo anterior", 120, "e"),
        ):
            self._tabla.heading(clave, text=titulo)
            self._tabla.column(clave, width=ancho, anchor=ancla)
        self._tabla.pack(fill="x", pady=(8, 0))
        self._tabla.bind("<Delete>", lambda _e: self._quitar_linea())
        self._tabla.bind("<Double-1>", self._editar_linea)  # CO-06

        resumen = ttk.Frame(self._tab_registrar)
        resumen.pack(fill="x", pady=4)
        ttk.Label(resumen, textvariable=self._suma).pack(side="left", padx=4)
        ttk.Label(resumen, textvariable=self._diferencia).pack(side="left", padx=16)
        ttk.Button(resumen, text="Limpiar", command=self._limpiar).pack(side="right", padx=4)
        ttk.Button(
            resumen,
            text="Confirmar factura (Ctrl+Enter)",
            style="Primario.TButton",
            command=self._confirmar,
        ).pack(side="right", padx=4)
        self.winfo_toplevel().bind("<Control-Return>", self._atajo_confirmar, add="+")
        ttk.Label(self._tab_registrar, textvariable=self._mensaje, foreground="#5B3E7E").pack(
            anchor="w"
        )

        # --- Facturas registradas ----------------------------------------------------------
        cols = ("documento", "fecha", "proveedor", "neto", "impuestos", "total", "estado")
        self._lista = ttk.Treeview(self._tab_facturas, columns=cols, show="headings", height=6)
        for clave, titulo, ancho, ancla in (
            ("documento", "Documento", 110, "w"),
            ("fecha", "Fecha", 100, "w"),
            ("proveedor", "Proveedor", 220, "w"),
            ("neto", "Neto", 100, "e"),
            ("impuestos", "Impuestos", 100, "e"),
            ("total", "Total", 100, "e"),
            ("estado", "Estado", 100, "w"),
        ):
            self._lista.heading(clave, text=titulo)
            self._lista.column(clave, width=ancho, anchor=ancla)
        self._lista.pack(fill="both", expand=True, pady=4)
        self._proveedores_tabla = ttk.Treeview(
            self._tab_proveedores,
            columns=("proveedor", "contacto", "facturas", "total", "ultima"),
            show="headings",
            height=14,
        )
        for clave, titulo, ancho, ancla in (
            ("proveedor", "Proveedor", 260, "w"),
            ("contacto", "Contacto", 200, "w"),
            ("facturas", "Facturas", 90, "e"),
            ("total", "Total comprado", 140, "e"),
            ("ultima", "Última compra", 120, "w"),
        ):
            self._proveedores_tabla.heading(clave, text=titulo)
            self._proveedores_tabla.column(clave, width=ancho, anchor=ancla)
        self._proveedores_tabla.pack(fill="both", expand=True)
        self._proveedores_tabla.bind("<Double-1>", lambda _e: self.editar_proveedor())  # CO-02
        ttk.Label(
            self._tab_proveedores,
            text="Crea uno con «Nuevo proveedor» o escríbelo al registrar su primera factura.",
            foreground="#666",
        ).pack(anchor="w", pady=4)
        self._refrescar_lista()

    # ------------------------------------------------------------------ montos --

    def _leer_monto(self, texto: str) -> int | None:
        try:
            return parsear_monto(texto) if texto.strip() else None
        except ValueError:
            return None

    def _poner(self, variable: tk.StringVar, monto: int) -> None:
        self._actualizando = True
        variable.set(formatear_clp(monto).lstrip("$"))
        self._actualizando = False

    def _al_editar_neto(self, _evento: object = None) -> None:
        self._neto_manual = True
        self._recalcular()

    def _al_editar_impuestos(self, _evento: object = None) -> None:
        self._impuestos_manual = True
        self._recalcular()

    def _recalcular(self) -> None:
        suma = sum(x.subtotal for x in self._lineas)
        if not self._neto_manual:
            self._poner(self._neto, suma) if suma else self._neto.set("")
        neto = self._leer_monto(self._neto.get()) or 0
        if not self._impuestos_manual:
            self._poner(self._impuestos, iva_de(neto)) if neto else self._impuestos.set("")
        impuestos = self._leer_monto(self._impuestos.get()) or 0
        self._total.set(f"Total: {formatear_clp(neto + impuestos)}")
        self._suma.set(f"Suma del detalle: {formatear_clp(suma)}")
        self._diferencia.set(f"Diferencia con el neto: {formatear_clp(neto - suma)}")

    # ------------------------------------------------------------------ lineas --

    def _agregar_linea(self) -> None:
        codigo = self._l_codigo.get().strip()
        if not codigo:
            messagebox.showerror("Compras", "Falta el código del producto")
            return
        producto = self._productos.obtener_por_codigo(codigo)
        if producto is None:
            messagebox.showerror("Compras", f"No existe un producto con código {codigo}")
            return
        texto = self._l_cantidad.get().strip().replace(",", ".")
        if not texto:
            messagebox.showerror("Compras", "Falta la cantidad")
            return
        if producto.unidad_venta is UnidadVenta.GRANEL:  # CO-05: «1k» y «1,5 kg» valen en granel
            texto = re.sub(r"\s*k(g|ilos?)?$", "", texto, flags=re.IGNORECASE)
        try:
            cantidad = Decimal(texto)
        except InvalidOperation:
            messagebox.showerror("Compras", "La cantidad debe ser un número, por ejemplo 10")
            return
        costo = self._leer_monto(self._l_costo.get())
        if costo is None:
            messagebox.showerror("Compras", "Falta el costo unitario neto (solo números)")
            return
        vence_texto = self._l_vence.get().strip()
        try:
            vence = datetime.strptime(vence_texto, "%Y-%m-%d").date() if vence_texto else None
        except ValueError:
            messagebox.showerror("Compras", "La fecha de vencimiento debe ser AAAA-MM-DD")
            return
        if producto.perecible and vence is None:
            messagebox.showerror(
                "Compras", f"{producto.nombre} es perecible: falta la fecha de vencimiento"
            )
            return
        try:
            self._lineas.append(
                LineaFactura(codigo, cantidad, costo, vence, self._l_lote.get().strip())
            )
        except ErrorDominio as error:
            messagebox.showerror("Compras", str(error))
            return
        for variable in (self._l_codigo, self._l_cantidad, self._l_costo, self._l_lote):
            variable.set("")
        self._l_vence.set("")
        self._refrescar_lineas()

    def _editar_linea(self, _evento: object = None) -> None:
        """CO-06: doble clic en una linea carga sus datos para corregirla y volver a agregarla."""
        seleccion = self._tabla.selection()
        if not seleccion:
            return
        linea = self._lineas.pop(self._tabla.index(seleccion[0]))
        self._l_codigo.set(linea.codigo_producto)
        self._l_cantidad.set(formatear_cantidad(linea.cantidad))
        self._l_costo.set(formatear_clp(linea.costo_unitario_neto).lstrip("$"))
        self._l_vence.set(linea.fecha_vencimiento.isoformat() if linea.fecha_vencimiento else "")
        self._l_lote.set(linea.codigo_lote)
        self._refrescar_lineas()
        self._mensaje.set("Corrige la línea y vuelve a agregarla.")

    def _actualizar_unidad(self, *_args: object) -> None:
        """CO-05: junto a la cantidad se ve la unidad del producto (kg si es a granel)."""
        producto = self._productos.obtener_por_codigo(self._l_codigo.get().strip())
        if producto is None:
            self._lbl_cantidad.config(text="Cantidad")
        elif producto.unidad_venta is UnidadVenta.GRANEL:
            self._lbl_cantidad.config(text="Cantidad (kg)")
        else:
            self._lbl_cantidad.config(text="Cantidad (unid.)")

    def _al_cambiar_pestana(self, _evento: object = None) -> None:
        """CO-04: si se deja una factura sin confirmar, se avisa (no se pierde en silencio)."""
        actual = self._pestanas.select()
        anterior, self._pestana_actual = self._pestana_actual, actual
        registrar = str(self._tab_registrar)
        if self._avisando or anterior != registrar or actual == registrar or not self._lineas:
            return
        self._avisando = True
        try:
            if messagebox.askyesno(
                "Factura sin confirmar",
                f"Hay una factura sin confirmar ({len(self._lineas)} líneas). Si no la "
                "confirmas, no se guarda y el stock no sube.\n\n¿Volver a ella para confirmarla?",
            ):
                self._pestanas.select(self._tab_registrar)
        finally:
            self._avisando = False

    def puede_salir(self) -> bool:
        """CO-04: al cambiar de modulo con una factura sin confirmar, se pregunta antes."""
        if not self._lineas:
            return True
        return messagebox.askyesno(
            "Factura sin confirmar",
            "Hay una factura sin confirmar: si sales ahora no se guarda.\n\n¿Salir igual?",
        )

    def _quitar_linea(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            return
        del self._lineas[self._tabla.index(seleccion[0])]
        self._refrescar_lineas()

    def _refrescar_lineas(self) -> None:
        self._tabla.delete(*self._tabla.get_children())
        for linea in self._lineas:
            producto = self._productos.obtener_por_codigo(linea.codigo_producto)
            anterior = producto.costo.neto.monto if producto and producto.costo else None
            self._tabla.insert(
                "",
                "end",
                values=(
                    producto.nombre if producto else linea.codigo_producto,
                    (
                        f"{formatear_cantidad(linea.cantidad)} kg"
                        if producto and producto.unidad_venta is UnidadVenta.GRANEL
                        else formatear_cantidad(linea.cantidad)
                    ),
                    formatear_clp(linea.costo_unitario_neto),
                    formatear_clp(linea.subtotal),
                    formatear_clp(anterior) if anterior is not None else "sin costo",
                ),
            )
        self._recalcular()

    # --------------------------------------------------------------- confirmar --

    def _atajo_confirmar(self, _evento: object = None) -> None:
        if self.winfo_ismapped():
            self._confirmar()

    def _confirmar(self) -> None:
        fecha_texto = self._fecha.get().strip()
        try:
            fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Compras", "La fecha debe ser AAAA-MM-DD")
            return
        neto = self._leer_monto(self._neto.get())
        if neto is None:
            messagebox.showerror("Compras", "Falta el monto neto (solo números)")
            return
        impuestos = self._leer_monto(self._impuestos.get())
        factura = FacturaCompra(
            proveedor=self._proveedor.get().strip(),
            numero=self._numero.get().strip(),
            fecha=fecha,
            neto=neto,
            impuestos=impuestos if impuestos is not None else iva_de(neto),
            lineas=list(self._lineas),
        )
        try:
            self._registrar.confirmar(factura)
        except ErrorDominio as error:
            messagebox.showerror("Compras", str(error))
            return
        self._mensaje.set(
            f"Factura {factura.numero} confirmada: costo actualizado y stock ingresado "
            f"({len(factura.lineas)} productos)"
        )
        self._limpiar()
        self._proveedor.config(values=self._nombres_proveedores())
        self._refrescar_lista()

    def _limpiar(self) -> None:
        self._lineas.clear()
        self._neto_manual = self._impuestos_manual = False
        self._numero.set("")
        self._proveedor.set("")
        self._fecha.set(date.today().isoformat())
        for variable in (self._l_codigo, self._l_cantidad, self._l_costo, self._l_lote):
            variable.set("")
        self._l_vence.set("")
        self._refrescar_lineas()

    def _nombres_proveedores(self) -> list[str]:
        """Los creados a mano y los que ya salieron en una factura, sin repetir."""
        if self._gestion_proveedores is not None:
            return self._gestion_proveedores.nombres()
        return self._facturas.proveedores()

    def _contactos_proveedores(self) -> dict[str, str]:
        if self._gestion_proveedores is None:
            return {}
        return {p.nombre: p.contacto for p in self._gestion_proveedores.repositorio.listar()}

    def nuevo_proveedor(self) -> None:
        """Formulario del proveedor nuevo; al crearlo queda elegido en la factura."""
        if self._gestion_proveedores is None:
            return

        def aceptar(datos: dict[str, str]) -> bool:
            try:
                proveedor = self._gestion_proveedores.crear(datos["nombre"], datos["contacto"])
            except ErrorDominio as error:
                messagebox.showerror("Compras", str(error))
                return False
            self._proveedor.config(values=self._nombres_proveedores())
            en_curso = self._proveedor.get().strip() if self._lineas else ""
            if en_curso:
                # CO-03: no se cambia el proveedor de una factura a medio hacer sin avisar.
                self._mensaje.set(
                    f"Proveedor «{proveedor.nombre}» creado. La factura en curso sigue con "
                    f"«{en_curso}»: cámbialo si corresponde."
                )
            else:
                self._proveedor.set(proveedor.nombre)
                self._mensaje.set(
                    f"Proveedor «{proveedor.nombre}» creado: ya se puede facturar con él."
                )
            self._refrescar_lista()
            iid = f"prov-{proveedor.nombre}"
            if self._proveedores_tabla.exists(iid):
                self._proveedores_tabla.selection_set(iid)
                self._proveedores_tabla.see(iid)
            if self._lineas:  # con una factura en curso se queda ahi, con sus lineas a la vista
                self._pestanas.select(self._tab_registrar)
            return True

        self.dialogo = pedir_formulario(
            self,
            "Nuevo proveedor",
            [("nombre", "Nombre (obligatorio)", "", None), ("contacto", "Contacto", "", None)],
            aceptar,
            "Crear proveedor",
        )

    def editar_proveedor(self) -> None:
        """CO-02: cambia nombre y contacto del proveedor elegido en la pestaña Proveedores."""
        if self._gestion_proveedores is None:
            return
        seleccion = self._proveedores_tabla.selection()
        if not seleccion:
            messagebox.showinfo(
                "Compras", "Elige un proveedor de la lista (pestaña Proveedores) para editarlo."
            )
            return
        actual = str(self._proveedores_tabla.item(seleccion[0], "values")[0])
        contacto = self._contactos_proveedores().get(actual, "")

        def aceptar(datos: dict[str, str]) -> bool:
            try:
                proveedor = self._gestion_proveedores.modificar(
                    actual, datos["nombre"], datos["contacto"]
                )
            except ErrorDominio as error:
                messagebox.showerror("Compras", str(error))
                return False
            self._proveedor.config(values=self._nombres_proveedores())
            if self._proveedor.get().strip() == actual:
                self._proveedor.set(proveedor.nombre)  # la factura en curso sigue con el mismo
            self._mensaje.set(f"Proveedor «{proveedor.nombre}» actualizado.")
            self._refrescar_lista()
            iid = f"prov-{proveedor.nombre}"
            if self._proveedores_tabla.exists(iid):
                self._proveedores_tabla.selection_set(iid)
            return True

        self.dialogo = pedir_formulario(
            self,
            "Editar proveedor",
            [
                ("nombre", "Nombre (obligatorio)", actual, None),
                ("contacto", "Contacto", contacto, None),
            ],
            aceptar,
            "Guardar",
        )

    def ir_a_registrar(self) -> None:
        self._pestanas.select(self._tab_registrar)

    def _refrescar_lista(self) -> None:
        self._lista.delete(*self._lista.get_children())
        facturas = self._facturas.listar()
        self._proveedores_tabla.delete(*self._proveedores_tabla.get_children())
        por_proveedor: dict[str, list] = {}
        for f in facturas:
            por_proveedor.setdefault(f.proveedor, []).append(f)
        contactos = self._contactos_proveedores()
        for nombre in self._nombres_proveedores() or sorted(por_proveedor, key=str.lower):
            lista = por_proveedor.get(nombre, [])
            self._proveedores_tabla.insert(
                "",
                "end",
                iid=f"prov-{nombre}",
                values=(
                    nombre,
                    contactos.get(nombre, ""),
                    len(lista),
                    formatear_clp(sum(x.total for x in lista)) if lista else "—",
                    max(x.fecha for x in lista).isoformat() if lista else "—",
                ),
            )
        for f in facturas:
            self._lista.insert(
                "",
                "end",
                values=(
                    f.numero,
                    f.fecha.isoformat(),
                    f.proveedor,
                    formatear_clp(f.neto),
                    formatear_clp(f.impuestos),
                    formatear_clp(f.total),
                    f.estado.value.capitalize(),
                ),
            )

    def al_mostrar(self) -> None:
        self._refrescar_lista()
