"""Caso de uso: registrar una merma o ajuste con motivo obligatorio (HU-INV-04).

Da de baja una cantidad (vencimiento, rotura, perdida, consumo interno, devolucion), deja un
registro que no se edita en `historial_ajustes_inventario` y descuenta tambien de los lotes
(primero el que vence antes) para que alertas y lotes sigan calzando con la existencia.
Un error se corrige con un movimiento inverso (ingresar stock), nunca editando el registro.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.ajustar_stock import AjustarStock
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioAjustes,
    RepositorioExistencias,
    RepositorioLotes,
)
from pos.aplicacion.sincronizacion import encolar_lote
from pos.dominio.errores import ReglaInventarioInvalida
from pos.dominio.inventario import AjusteInventario, MotivoAjuste
from pos.dominio.lotes import consumir_fefo


@dataclass
class RegistrarMerma:
    repositorio_existencias: RepositorioExistencias
    repositorio_ajustes: RepositorioAjustes
    repositorio_lotes: RepositorioLotes | None = None
    cola: ColaSincronizacion | None = None
    auditor: Auditor | None = None

    def ejecutar(
        self,
        codigo_producto: str,
        cantidad_a_dar_de_baja: Decimal | float | str,
        motivo: MotivoAjuste,
        usuario: str,
        observacion: str = "",
    ) -> AjusteInventario:
        try:
            baja = Decimal(str(cantidad_a_dar_de_baja))
        except InvalidOperation as exc:
            raise ReglaInventarioInvalida("La cantidad a dar de baja debe ser un numero") from exc
        if baja <= 0:
            raise ReglaInventarioInvalida("La cantidad a dar de baja debe ser mayor que cero")
        existencia = self.repositorio_existencias.obtener(codigo_producto)
        actual = existencia.cantidad if existencia is not None else Decimal("0")
        if baja > actual:
            raise ReglaInventarioInvalida(
                f"No hay stock suficiente de {codigo_producto}: hay {actual} y se quieren dar "
                f"de baja {baja}"
            )
        ajuste = AjustarStock(
            self.repositorio_existencias, self.repositorio_ajustes, cola=self.cola
        ).ejecutar(codigo_producto, actual - baja, motivo, usuario, observacion)
        self._descontar_lotes(codigo_producto, baja)
        if self.auditor is not None:
            self.auditor.registrar(
                f"Merma ({motivo.value})",
                codigo_producto,
                str(ajuste.cantidad_anterior),
                str(ajuste.cantidad_nueva),
                {"observacion": observacion},
            )
        return ajuste

    def _descontar_lotes(self, codigo: str, cantidad: Decimal) -> None:
        if self.repositorio_lotes is None:
            return
        lotes = [x for x in self.repositorio_lotes.por_producto(codigo) if x.saldo > 0]
        antes = {x.uuid: x.saldo for x in lotes}
        consumir_fefo(lotes, cantidad)
        for lote in lotes:
            if lote.saldo != antes[lote.uuid]:
                self.repositorio_lotes.guardar(lote)
                encolar_lote(self.cola, lote)
