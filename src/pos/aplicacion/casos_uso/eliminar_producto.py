"""Caso de uso: eliminar un producto creado por error (CA-22).

Solo se borra uno SIN historia (ventas, lotes, facturas, movimientos ni stock). Si la tiene, no se
elimina: los reportes pasados, la auditoria y la copia en Supabase quedarian apuntando a un
producto que ya no existe, y se ofrece desactivarlo. El borrado queda en la auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.puertos import ColaSincronizacion, RepositorioProductos
from pos.aplicacion.sincronizacion import encolar_producto_eliminado
from pos.dominio.errores import DatosProductoInvalidos


class ProductoConHistoria(DatosProductoInvalidos):
    """El producto tiene historia: no se elimina, se desactiva."""


@dataclass
class EliminarProducto:
    repositorio: RepositorioProductos
    cola: ColaSincronizacion | None = None
    auditor: Auditor | None = None

    def puede_eliminarse(self, codigo: str) -> bool:
        return not self.repositorio.tiene_historia(codigo)

    def ejecutar(self, codigo: str) -> None:
        producto = self.repositorio.obtener_por_codigo(codigo)
        if producto is None:
            raise DatosProductoInvalidos(f"No existe un producto con código {codigo}")
        if self.repositorio.tiene_historia(codigo):
            raise ProductoConHistoria(
                f"«{producto.nombre}» tiene ventas, lotes, facturas o movimientos: no se puede "
                "eliminar. Puedes desactivarlo y su historial se conserva."
            )
        self.repositorio.eliminar(codigo)
        encolar_producto_eliminado(self.cola, codigo)
        if self.auditor is not None:
            self.auditor.registrar(
                "Eliminación de producto", f"{producto.nombre} ({codigo})", "Existía", "Eliminado"
            )
