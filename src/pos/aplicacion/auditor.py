"""Deja rastro de quien hizo que (HU-USR-03).

`usuario` es una funcion y no un nombre fijo porque la sesion cambia (se cierra y entra otra
persona) sin reconstruir los casos de uso.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pos.aplicacion.puertos import RepositorioAuditoria


@dataclass
class Auditor:
    repositorio: RepositorioAuditoria
    usuario: Callable[[], str]

    def registrar(
        self,
        accion: str,
        registro: str = "",
        antes: str = "",
        despues: str = "",
        detalle: dict | None = None,
    ) -> None:
        self.repositorio.registrar(
            self.usuario() or "sistema", accion, detalle or {}, registro, antes, despues
        )
