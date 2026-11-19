"""Caso de uso: imprimir el comprobante, reimprimir el ultimo, imprimir el corte y abrir el cajon.

HU-VTA-06. El comprobante es solo el detalle de lo vendido; la boleta la emite el terminal. Si la
impresora falla, la venta ya esta registrada: el error se devuelve para que la pantalla avise, pero
nunca deshace una venta.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pos.aplicacion.puertos import (
    Impresora,
    RepositorioClientes,
    RepositorioConfiguracion,
    RepositorioProductos,
    RepositorioVentas,
)
from pos.dominio.caja import Arqueo, TurnoCaja
from pos.dominio.comprobante import comprobante_de_venta, corte_de_caja, ticket_de_prueba
from pos.dominio.errores import ErrorImpresion
from pos.dominio.pagos import MedioPago
from pos.dominio.ventas import Venta


@dataclass
class ImprimirComprobante:
    # Una funcion y no una impresora: la configuracion (nombre de la impresora) puede cambiar en F7.
    impresora: Callable[[], Impresora]
    repositorio_productos: RepositorioProductos
    repositorio_ventas: RepositorioVentas
    configuracion: RepositorioConfiguracion | None = None
    repositorio_clientes: RepositorioClientes | None = None
    cajera: Callable[[], str] = lambda: ""

    def comprobante(self, venta: Venta) -> None:
        """Imprime el detalle de la venta; abre el cajon si hubo efectivo."""
        nombres = self._nombres(venta)
        cliente = ""
        if venta.cliente_id is not None and self.repositorio_clientes is not None:
            registro = self.repositorio_clientes.obtener(venta.cliente_id)
            cliente = registro.nombre if registro else ""
        lineas = comprobante_de_venta(venta, nombres, cliente, self.cajera())
        self._imprimir(lineas, self._abre_cajon(venta))

    def reimprimir_ultimo(self) -> Venta:
        venta = self.repositorio_ventas.ultima()
        if venta is None:
            raise ErrorImpresion("Todavia no hay ventas para reimprimir")
        self.comprobante_sin_cajon(venta)
        return venta

    def comprobante_sin_cajon(self, venta: Venta) -> None:
        """Reimpresion: el cajon no se vuelve a abrir."""
        self._imprimir(
            comprobante_de_venta(venta, self._nombres(venta), cajera=self.cajera()), False
        )

    def corte(self, turno: TurnoCaja, arqueo: Arqueo) -> None:
        self._imprimir(corte_de_caja(turno, arqueo), False)

    def prueba(self, abrir_cajon: bool = False) -> None:
        self._imprimir(ticket_de_prueba(), abrir_cajon)

    def abrir_cajon_si_hubo_efectivo(self, venta: Venta) -> None:
        """Para «cobrar solo registrando»: igual entra efectivo a la gaveta."""
        if self._abre_cajon(venta):
            try:
                self.impresora().abrir_cajon()
            except ErrorImpresion:
                raise
            except Exception as exc:  # noqa: BLE001
                raise ErrorImpresion(f"No se pudo abrir el cajon: {exc}") from exc

    # ------------------------------------------------------------------ privados --

    def _nombres(self, venta: Venta) -> dict[str, str]:
        nombres = {}
        for detalle in venta.detalles:
            producto = self.repositorio_productos.obtener_por_codigo(detalle.producto_codigo)
            nombres[detalle.producto_codigo] = (
                producto.nombre if producto else detalle.producto_codigo
            )
        return nombres

    def _abre_cajon(self, venta: Venta) -> bool:
        quiere = self.configuracion.obtener("abrir_cajon") == 1 if self.configuracion else True
        return quiere and any(p.medio is MedioPago.EFECTIVO for p in venta.pagos)

    def _imprimir(self, lineas: list[str], abrir_cajon: bool) -> None:
        try:
            self.impresora().imprimir(lineas, abrir_cajon)
        except ErrorImpresion:
            raise
        except Exception as exc:  # noqa: BLE001 - cualquier falla del equipo se informa igual
            raise ErrorImpresion(f"No se pudo imprimir: {exc}") from exc
