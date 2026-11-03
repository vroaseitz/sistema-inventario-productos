"""Caso de uso: confirmar una factura de compra (HU-CMP-01, HU-CMP-02).

Al confirmar, el costo neto de cada producto se actualiza desde el documento del proveedor (asi
un producto sin costo deja de reportar 100 % de ganancia) y la mercaderia entra al inventario,
con su lote si el producto vence. Todo se valida ANTES de tocar nada: o entra la factura
completa o no entra.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioCategorias,
    RepositorioExistencias,
    RepositorioFacturasCompra,
    RepositorioLotes,
    RepositorioProductos,
)
from pos.aplicacion.registro_movimientos import RegistroMovimientos
from pos.aplicacion.sincronizacion import encolar_producto
from pos.dominio.compras import FacturaCompra
from pos.dominio.errores import ReglaCompraInvalida
from pos.dominio.value_objects import Costo, Dinero


@dataclass
class RegistrarFacturaCompra:
    repositorio_facturas: RepositorioFacturasCompra
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias
    repositorio_lotes: RepositorioLotes
    cola: ColaSincronizacion | None = None
    repositorio_categorias: RepositorioCategorias | None = None
    auditor: Auditor | None = None
    movimientos: RegistroMovimientos | None = None

    def confirmar(self, factura: FacturaCompra, hoy: date | None = None) -> FacturaCompra:
        hoy = hoy or date.today()
        factura.validar()
        if self.repositorio_facturas.existe(factura.proveedor, factura.numero):
            raise ReglaCompraInvalida(
                f"Ya existe la factura {factura.numero} de {factura.proveedor}"
            )
        for linea in factura.lineas:
            producto = self.repositorio_productos.obtener_por_codigo(linea.codigo_producto)
            if producto is None:
                raise ReglaCompraInvalida(f"No existe el producto {linea.codigo_producto}")
            if producto.perecible and linea.fecha_vencimiento is None:
                raise ReglaCompraInvalida(
                    f"{producto.nombre} es perecible: falta la fecha de vencimiento del lote"
                )
            if linea.fecha_vencimiento is not None and linea.fecha_vencimiento < hoy:
                raise ReglaCompraInvalida(f"El lote de {producto.nombre} ya esta vencido")

        ingresar = IngresarStock(
            self.repositorio_productos,
            self.repositorio_existencias,
            self.repositorio_lotes,
            cola=self.cola,
            movimientos=self.movimientos,
        )
        for linea in factura.lineas:
            producto = self.repositorio_productos.obtener_por_codigo(linea.codigo_producto)
            linea.costo_anterior = producto.costo.neto.monto if producto.costo else None
            # Costo neto sin impuestos (ADR 0004): el margen se calcula sobre el neto.
            producto.costo = Costo(neto=Dinero(linea.costo_unitario_neto), iva=Dinero(0))
            self.repositorio_productos.guardar(producto)
            categoria = (
                self.repositorio_categorias.nombre_de(producto.categoria_id)
                if self.repositorio_categorias
                else None
            )
            encolar_producto(self.cola, producto, categoria)
            ingresar.ejecutar(
                linea.codigo_producto,
                linea.cantidad,
                f"Factura {factura.numero}",
                linea.fecha_vencimiento,
                hoy=hoy,
                codigo_lote=linea.codigo_lote,
            )
        self.repositorio_facturas.guardar(factura)
        if self.auditor is not None:
            self.auditor.registrar(
                "Confirmación de factura",
                f"{factura.numero} · {factura.proveedor}",
                "Borrador",
                "Confirmada",
            )
        return factura
