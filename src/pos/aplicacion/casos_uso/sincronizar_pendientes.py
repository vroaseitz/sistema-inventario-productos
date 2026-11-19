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


MENSAJE_CIERRE_ENVIADO = "Jornada cerrada. Datos enviados a la nube."


def mensaje_cierre_pendientes(cuantas: int) -> str:
    return (
        f"Jornada cerrada. Quedan {cuantas} operaciones sin enviar; se enviarán en el próximo "
        "cierre o con el botón Sincronizar."
    )


@dataclass
class SincronizarAlCierre:
    """SY-01 (decision del 18-11): al cerrar la jornada se envia lo pendiente a la nube.

    Nunca deshace ni bloquea el cierre (la jornada ya quedo cerrada en el PC): un solo intento,
    sin reintentar en bucle, y sin Supabase configurado no hace nada ni muestra error.
    """

    cola: ColaSincronizacion | None
    publicador: PublicadorRemoto | None

    def ejecutar(self) -> str | None:
        """Texto para la usuaria, o None si no hay nada que informar (sin Supabase)."""
        if self.cola is None or self.publicador is None:
            return None
        try:
            SincronizarPendientes(self.cola, self.publicador).ejecutar()
            quedan = len(self.cola.pendientes())
        except Exception:  # la sincronizacion jamas debe romper el cierre
            return None
        return MENSAJE_CIERRE_ENVIADO if quedan == 0 else mensaje_cierre_pendientes(quedan)
