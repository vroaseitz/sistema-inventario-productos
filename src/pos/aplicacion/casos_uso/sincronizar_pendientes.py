"""Caso de uso: sincronizar las operaciones pendientes con el destino remoto.

Recorre la cola local y publica cada operacion. Si una falla, corta el proceso pero
NO pierde ni duplica lo ya hecho: lo publicado quedo marcado como 'synced' y lo
pendiente sigue 'pending'. Al reintentar, solo se procesa lo pendiente. Esto hace la
sincronizacion reanudable y segura frente a cortes de energia o de red.
"""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.puertos import ColaSincronizacion, PublicadorRemoto


@dataclass
class ResultadoSincronizacion:
    sincronizadas: int
    fallo_en: str | None = None


@dataclass
class SincronizarPendientes:
    cola: ColaSincronizacion
    publicador: PublicadorRemoto

    def ejecutar(self) -> ResultadoSincronizacion:
        sincronizadas = 0
        for operacion in self.cola.pendientes():
            try:
                self.publicador.publicar(operacion)
            except Exception:
                # Se detiene sin marcar la fallida: quedara pendiente para el reintento.
                return ResultadoSincronizacion(
                    sincronizadas=sincronizadas, fallo_en=operacion["id_cliente"]
                )
            self.cola.marcar_sincronizada(operacion["id_cliente"])
            sincronizadas += 1
        return ResultadoSincronizacion(sincronizadas=sincronizadas)
