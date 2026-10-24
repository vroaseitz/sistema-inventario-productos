"""GUI de escritorio con Tkinter para venta y caja (HU-VTA-01/03/04, HU-CAJ-01/02/04).

Mismo criterio que app_tkinter.py: la ventana recibe los casos de uso ya armados
por constructor y solo orquesta la vista. Toda la logica de negocio (redondeo,
vuelto, arqueo, validaciones) vive en dominio/aplicacion y ya esta probada en
tests/unitarias/test_pagos.py, test_ventas.py, test_caja.py y
tests/integracion/test_ventas_caja_e2e.py.
"""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, simpledialog, ttk

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.puertos import RepositorioProductos, RepositorioTurnosCaja
from pos.dominio.caja import TipoMovimientoCaja
from pos.dominio.errores import ErrorDominio
from pos.dominio.pagos import MedioPago, Pago, calcular_cobro_efectivo
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import Venta

USUARIO_DEMO = 1  # sin login todavia (ver docs/04-requisitos-no-funcionales)


class VentanaVentas(tk.Tk):
    def __init__(
        self,
        repositorio_turnos: RepositorioTurnosCaja,
        repositorio_productos: RepositorioProductos,
        registrar_venta: RegistrarVenta,
        abrir_turno: AbrirTurnoCaja,
        cerrar_turno: CerrarTurnoCaja,
        registrar_movimiento: RegistrarMovimientoCaja,
    ) -> None:
        super().__init__()
        self._repo_turnos = repositorio_turnos
        self._repo_productos = repositorio_productos
        self._registrar_venta = registrar_venta
        self._abrir_turno = abrir_turno
        self._cerrar_turno = cerrar_turno
        self._registrar_movimiento = registrar_movimiento

        self._venta: Venta | None = None

        self.title("NaturalSur - Venta y Caja")
        self.geometry("820x600")
        self._construir()
        self._refrescar_turno()

    # ------------------------------------------------------------------ UI --

    def _construir(self) -> None:
        marco_turno = ttk.LabelFrame(self, text="Turno de caja")
        marco_turno.pack(fill="x", padx=12, pady=8)

        self._lbl_turno = ttk.Label(marco_turno, text="Sin turno abierto")
        self._lbl_turno.pack(side="left", padx=8, pady=6)

        ttk.Button(marco_turno, text="Abrir turno", command=self._abrir_turno_ui).pack(
            side="right", padx=4, pady=6
        )
        ttk.Button(marco_turno, text="Movimiento de caja", command=self._movimiento_ui).pack(
            side="right", padx=4, pady=6
        )
        ttk.Button(marco_turno, text="Cerrar turno (arqueo)", command=self._cerrar_turno_ui).pack(
            side="right", padx=4, pady=6
        )

        marco_venta = ttk.LabelFrame(self, text="Venta en curso")
        marco_venta.pack(fill="x", padx=12, pady=8)

        ttk.Label(marco_venta, text="Codigo").grid(row=0, column=0, padx=4, pady=6)
        self._entrada_codigo = ttk.Entry(marco_venta, width=14)
        self._entrada_codigo.grid(row=0, column=1, padx=4, pady=6)

        ttk.Label(marco_venta, text="Cantidad").grid(row=0, column=2, padx=4, pady=6)
        self._entrada_cantidad = ttk.Entry(marco_venta, width=8)
        self._entrada_cantidad.insert(0, "1")
        self._entrada_cantidad.grid(row=0, column=3, padx=4, pady=6)

        ttk.Button(marco_venta, text="Agregar", command=self._agregar_producto).grid(
            row=0, column=4, padx=8, pady=6
        )
        ttk.Button(marco_venta, text="Nueva venta", command=self._nueva_venta).grid(
            row=0, column=5, padx=4, pady=6
        )

        columnas = ("codigo", "nombre", "cantidad", "precio", "subtotal")
        self._tabla = ttk.Treeview(self, columns=columnas, show="headings", height=8)
        for col, titulo in zip(
            columnas, ("Codigo", "Nombre", "Cantidad", "Precio", "Subtotal"), strict=True
        ):
            self._tabla.heading(col, text=titulo)
        self._tabla.pack(fill="both", expand=True, padx=12, pady=4)

        self._lbl_total = ttk.Label(self, text="Total: $0", font=("TkDefaultFont", 12, "bold"))
        self._lbl_total.pack(anchor="e", padx=16)

        marco_pago = ttk.LabelFrame(self, text="Pago")
        marco_pago.pack(fill="x", padx=12, pady=8)

        self._medio = tk.StringVar(value=MedioPago.EFECTIVO.value)
        ttk.Combobox(
            marco_pago,
            textvariable=self._medio,
            values=[m.value for m in MedioPago],
            width=16,
            state="readonly",
        ).grid(row=0, column=0, padx=4, pady=6)

        ttk.Label(marco_pago, text="Monto").grid(row=0, column=1, padx=4, pady=6)
        self._entrada_monto_pago = ttk.Entry(marco_pago, width=10)
        self._entrada_monto_pago.grid(row=0, column=2, padx=4, pady=6)

        ttk.Button(marco_pago, text="Agregar pago", command=self._agregar_pago).grid(
            row=0, column=3, padx=8, pady=6
        )
        ttk.Button(marco_pago, text="Cobrar y cerrar venta", command=self._cerrar_venta).grid(
            row=0, column=4, padx=8, pady=6
        )

        self._lbl_pagado = ttk.Label(self, text="Pagado: $0 / A cobrar: $0")
        self._lbl_pagado.pack(anchor="e", padx=16, pady=(0, 8))

    # -------------------------------------------------------------- Turno --

    def _refrescar_turno(self) -> None:
        turno = self._repo_turnos.obtener_abierto()
        if turno is None:
            self._lbl_turno.config(text="Sin turno abierto")
        else:
            self._lbl_turno.config(
                text=f"Turno #{turno.id} abierto - fondo inicial ${turno.fondo_inicial.monto}"
            )

    def _abrir_turno_ui(self) -> None:
        monto = simpledialog.askinteger(
            "Abrir turno", "Fondo inicial (CLP):", initialvalue=15_000, minvalue=0
        )
        if monto is None:
            return
        try:
            self._abrir_turno.ejecutar(usuario_id=USUARIO_DEMO, fondo_inicial=Dinero(monto))
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo abrir el turno", str(exc))
        self._refrescar_turno()

    def _cerrar_turno_ui(self) -> None:
        contado = simpledialog.askinteger(
            "Cerrar turno", "Efectivo contado (CLP):", minvalue=0
        )
        if contado is None:
            return
        try:
            arqueo = self._cerrar_turno.ejecutar(efectivo_contado=Dinero(contado))
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo cerrar el turno", str(exc))
            return
        detalle = "\n".join(
            f"{medio.value}: ${monto.monto}" for medio, monto in arqueo.totales_por_medio.items()
        )
        messagebox.showinfo(
            "Arqueo de cierre",
            f"{detalle}\n\nEfectivo esperado: ${arqueo.efectivo_esperado}\n"
            f"Efectivo contado: ${arqueo.efectivo_contado.monto}\n"
            f"Diferencia: ${arqueo.diferencia}",
        )
        self._refrescar_turno()

    def _movimiento_ui(self) -> None:
        tipo_str = simpledialog.askstring("Movimiento de caja", "Tipo (retiro/ingreso):")
        if not tipo_str:
            return
        try:
            tipo = TipoMovimientoCaja(tipo_str.strip().lower())
        except ValueError:
            messagebox.showerror("Tipo invalido", "Debe ser 'retiro' o 'ingreso'")
            return
        monto = simpledialog.askinteger("Movimiento de caja", "Monto (CLP):", minvalue=1)
        if monto is None:
            return
        motivo = simpledialog.askstring("Movimiento de caja", "Motivo (obligatorio):")
        try:
            self._registrar_movimiento.ejecutar(tipo, Dinero(monto), motivo or "")
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo registrar el movimiento", str(exc))

    # -------------------------------------------------------------- Venta --

    def _nueva_venta(self) -> None:
        try:
            self._venta = self._registrar_venta.iniciar(usuario_id=USUARIO_DEMO)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo iniciar la venta", str(exc))
            return
        self._refrescar_ticket()

    def _venta_actual(self) -> Venta | None:
        if self._venta is None:
            messagebox.showwarning("Sin venta", "Primero iniciá una venta nueva")
        return self._venta

    def _agregar_producto(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        codigo = self._entrada_codigo.get().strip()
        try:
            cantidad = Decimal(self._entrada_cantidad.get().strip() or "1")
        except InvalidOperation:
            messagebox.showerror("Cantidad invalida", "La cantidad debe ser un numero")
            return
        try:
            self._registrar_venta.agregar_producto(venta, codigo, cantidad)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo agregar el producto", str(exc))
            return
        self._entrada_codigo.delete(0, "end")
        self._refrescar_ticket()

    def _refrescar_ticket(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        venta = self._venta
        if venta is None:
            self._lbl_total.config(text="Total: $0")
            self._lbl_pagado.config(text="Pagado: $0 / A cobrar: $0")
            return
        for detalle in venta.detalles:
            producto = self._repo_productos.obtener_por_codigo(detalle.producto_codigo)
            nombre = producto.nombre if producto else "?"
            self._tabla.insert(
                "",
                "end",
                values=(
                    detalle.producto_codigo,
                    nombre,
                    detalle.cantidad,
                    detalle.precio_unitario.monto,
                    detalle.subtotal.monto,
                ),
            )
        self._lbl_total.config(text=f"Total: ${venta.total.monto}")
        self._lbl_pagado.config(
            text=f"Pagado: ${venta.total_pagado.monto} / A cobrar: ${venta.total_a_cobrar.monto}"
        )

    def _agregar_pago(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        try:
            monto = int(self._entrada_monto_pago.get().strip())
        except ValueError:
            messagebox.showerror("Monto invalido", "El monto debe ser un numero entero")
            return

        medio = MedioPago(self._medio.get())
        try:
            if medio is MedioPago.EFECTIVO:
                # El monto ingresado es lo que entrega el cliente; el que cubre el
                # pago es el total a cobrar ya redondeado (HU-VTA-04).
                resto = Dinero(venta.total.monto - venta.total_pagado.monto)
                cobro = calcular_cobro_efectivo(resto, monto_entregado=Dinero(monto))
                pago = Pago(medio=medio, monto=cobro.total_redondeado, cobro_efectivo=cobro)
                if cobro.vuelto.monto:
                    messagebox.showinfo("Vuelto", f"Vuelto: ${cobro.vuelto.monto}")
            else:
                pago = Pago(medio=medio, monto=Dinero(monto))
            self._registrar_venta.agregar_pago(venta, pago)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo agregar el pago", str(exc))
            return
        self._entrada_monto_pago.delete(0, "end")
        self._refrescar_ticket()

    def _cerrar_venta(self) -> None:
        venta = self._venta_actual()
        if venta is None:
            return
        try:
            self._registrar_venta.cerrar(venta)
        except ErrorDominio as exc:
            messagebox.showerror("No se pudo cerrar la venta", str(exc))
            return
        messagebox.showinfo("Venta cerrada", f"Venta #{venta.id} registrada con exito")
        self._venta = None
        self._refrescar_ticket()


def main() -> None:
    from pos.infraestructura.config import Config
    from pos.infraestructura.sqlite.conexion import crear_conexion
    from pos.infraestructura.sqlite.esquema import crear_esquema
    from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
    from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
    from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
    from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite

    config = Config.desde_entorno()
    conexion = crear_conexion(config.sqlite_path)
    crear_esquema(conexion)

    repo_productos = RepositorioProductosSQLite(conexion)
    repo_existencias = RepositorioExistenciasSQLite(conexion)
    repo_turnos = RepositorioTurnosCajaSQLite(conexion)
    repo_ventas = RepositorioVentasSQLite(conexion)

    registrar_venta = RegistrarVenta(repo_ventas, repo_turnos, repo_productos, repo_existencias)
    abrir_turno = AbrirTurnoCaja(repo_turnos)
    cerrar_turno = CerrarTurnoCaja(repo_turnos, repo_ventas)
    registrar_movimiento = RegistrarMovimientoCaja(repo_turnos)

    VentanaVentas(
        repo_turnos,
        repo_productos,
        registrar_venta,
        abrir_turno,
        cerrar_turno,
        registrar_movimiento,
    ).mainloop()


if __name__ == "__main__":
    main()
