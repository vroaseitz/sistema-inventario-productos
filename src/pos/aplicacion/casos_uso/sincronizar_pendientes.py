"""Caso de uso: sincronizar las operaciones pendientes con el destino remoto.

Recorre la cola local y publica cada operacion. Si una falla, corta el proceso pero
NO pierde ni duplica lo ya hecho: lo publicado quedo marcado como 'synced' y lo
pendiente sigue 'pending'. Al reintentar, solo se procesa lo pendiente. Esto hace la
sincronizacion reanudable y segura frente a cortes de energia o de red.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from pos.aplicacion.puertos import ColaSincronizacion, PublicadorRemoto


@dataclass
class ResultadoSincronizacion:
    sincronizadas: int
    fallo_en: str | None = None
    incompleto: bool = False  # se acabo el tiempo dado; lo que falta sigue pendiente


@dataclass
class SincronizarPendientes:
    cola: ColaSincronizacion
    publicador: PublicadorRemoto
    reloj: Callable[[], float] = time.monotonic

    def ejecutar(self, limite_segundos: float | None = None) -> ResultadoSincronizacion:
        """Publica lo pendiente en orden. Con `limite_segundos` se detiene al pasarse (el resto
        queda pendiente, sin perderse), para no dejar la pantalla esperando minutos."""
        try:
            return self._publicar_todo(limite_segundos)
        finally:
            cerrar = getattr(self.publicador, "cerrar", None)
            if callable(cerrar):
                cerrar()  # suelta la conexion reutilizada al terminar la tanda

    def _publicar_todo(self, limite_segundos: float | None) -> ResultadoSincronizacion:
        inicio = self.reloj()
        sincronizadas = 0
        for operacion in self.cola.pendientes():
            if limite_segundos is not None and self.reloj() - inicio >= limite_segundos:
                return ResultadoSincronizacion(sincronizadas=sincronizadas, incompleto=True)
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
    # Tras una migracion hay miles de operaciones pendientes: al cierre se envia lo que alcance en
    # este tiempo y el resto sale en el cierre siguiente o con el boton «Sincronizar».
    limite_segundos: float = 45.0
    reloj: Callable[[], float] = time.monotonic

    def ejecutar(self) -> str | None:
        """Texto para la usuaria, o None si no hay nada que informar (sin Supabase)."""
        if self.cola is None or self.publicador is None:
            return None
        try:
            SincronizarPendientes(self.cola, self.publicador, self.reloj).ejecutar(
                self.limite_segundos
            )
            quedan = len(self.cola.pendientes())
        except Exception:  # la sincronizacion jamas debe romper el cierre
            return None
        return MENSAJE_CIERRE_ENVIADO if quedan == 0 else mensaje_cierre_pendientes(quedan)
