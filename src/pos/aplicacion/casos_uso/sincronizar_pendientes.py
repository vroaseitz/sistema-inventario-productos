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

from pos.aplicacion.puertos import (
    ColaSincronizacion,
    OperacionIncompleta,
    OperacionRechazada,
    PublicadorRemoto,
)


@dataclass
class ResultadoSincronizacion:
    sincronizadas: int
    fallo_en: str | None = None
    incompleto: bool = False  # se acabo el tiempo dado; lo que falta sigue pendiente
    rechazadas: int = (
        0  # el destino las rechazo por sus datos: quedaron aparte, sin frenar al resto
    )


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
        # Lo rechazado antes vuelve a intentarse: si la causa ya se arreglo (p. ej. se aplico una
        # migracion en la nube), esta vez pasa; si no, se aparta de nuevo sin frenar a las demas.
        reencolar = getattr(self.cola, "reencolar_rechazadas", None)
        if callable(reencolar):
            reencolar()
        inicio = self.reloj()
        sincronizadas = 0
        rechazadas = 0
        claves_rechazadas: set[str] = set()
        for operacion in self.cola.pendientes():
            if limite_segundos is not None and self.reloj() - inicio >= limite_segundos:
                return ResultadoSincronizacion(
                    sincronizadas, incompleto=True, rechazadas=rechazadas
                )
            try:
                self.publicador.publicar(operacion)
            except OperacionRechazada as exc:
                # Anti-bucle: un dato que la nube no acepta no se reintenta eternamente ni frena
                # a las demas; queda aparte con su motivo, a la vista.
                self._rechazar(operacion, str(exc))
                rechazadas += 1
                claves_rechazadas |= _claves_de(operacion)
                continue
            except OperacionIncompleta:
                padre = _claves_de(operacion) & claves_rechazadas
                if padre:
                    # Depende de algo que la nube rechazo (un producto, una venta, un cliente):
                    # no llegara hasta que eso se arregle, pero no debe frenar a las demas.
                    nombre = sorted(padre)[0].replace(":", " ")
                    self._rechazar(operacion, f"Depende de {nombre}, que fue rechazado")
                    rechazadas += 1
                    continue
                return ResultadoSincronizacion(
                    sincronizadas, fallo_en=operacion["id_cliente"], rechazadas=rechazadas
                )
            except Exception:
                # Sin conexion u otro fallo pasajero: se detiene sin marcar la fallida, que
                # queda pendiente para el reintento.
                return ResultadoSincronizacion(
                    sincronizadas, fallo_en=operacion["id_cliente"], rechazadas=rechazadas
                )
            self.cola.marcar_sincronizada(operacion["id_cliente"])
            sincronizadas += 1
        return ResultadoSincronizacion(sincronizadas, rechazadas=rechazadas)

    def _rechazar(self, operacion: dict, motivo: str) -> None:
        marcar = getattr(self.cola, "marcar_rechazada", None)
        if callable(marcar):
            marcar(operacion["id_cliente"], motivo)


def _claves_de(operacion: dict) -> set[str]:
    """A que cosas se refiere la operacion (producto, venta, cliente), para que un rechazo se
    arrastre a lo que depende de el y a nada mas."""
    d = operacion.get("datos") or {}
    claves: set[str] = set()
    for campo in ("codigo", "codigo_producto"):
        if d.get(campo):
            claves.add(f"producto:{d[campo]}")
    if operacion.get("entidad") in ("venta", "venta_anular") and d.get("uuid"):
        claves.add(f"venta:{d['uuid']}")
    cliente = d.get("cliente") if isinstance(d.get("cliente"), dict) else d
    if operacion.get("entidad") in ("cliente", "movimiento_cliente") and cliente.get("id"):
        claves.add(f"{cliente['id']}")  # ya viene como «cliente:<id>»
    return claves


MENSAJE_CIERRE_ENVIADO = "Jornada cerrada. Datos enviados a la nube."


def mensaje_cierre_pendientes(cuantas: int) -> str:
    return (
        f"Jornada cerrada. Quedan {cuantas} operaciones sin enviar; se enviarán en el próximo "
        "cierre o con el botón Sincronizar."
    )


def mensaje_rechazadas(cuantas: int) -> str:
    return (
        f"La nube rechazó {cuantas} operaciones por sus datos. Quedaron guardadas en este "
        "computador y no se pierden; avisa a soporte para revisarlas."
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
            return (
                "Jornada cerrada. No se pudo enviar a la nube; se reintentará en el próximo "
                "cierre o con el botón Sincronizar."
            )
        rechazadas = getattr(self.cola, "rechazadas", None)
        n_rechazadas = len(rechazadas()) if callable(rechazadas) else 0
        texto = MENSAJE_CIERRE_ENVIADO if quedan == 0 else mensaje_cierre_pendientes(quedan)
        if n_rechazadas:
            texto = (
                texto.replace(MENSAJE_CIERRE_ENVIADO, "Jornada cerrada.")
                + " "
                + (mensaje_rechazadas(n_rechazadas))
            )
        return texto
