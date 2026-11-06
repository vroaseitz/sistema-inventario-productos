"""Deja rastro de quien hizo que (HU-USR-03).

`usuario` es una funcion y no un nombre fijo porque la sesion cambia (se cierra y entra otra
persona) sin reconstruir los casos de uso.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pos.aplicacion.puertos import ColaSincronizacion, RepositorioAuditoria
from pos.aplicacion.sincronizacion import encolar_auditoria


@dataclass
class Auditor:
    repositorio: RepositorioAuditoria
    usuario: Callable[[], str]
    cola: ColaSincronizacion | None = None

    def registrar(
        self,
        accion: str,
        registro: str = "",
        antes: str = "",
        despues: str = "",
        detalle: dict | None = None,
    ) -> None:
        quien = self.usuario() or "sistema"
        id_local = self.repositorio.registrar(
            quien, accion, detalle or {}, registro, antes, despues
        )
        encolar_auditoria(
            self.cola,
            id_local,
            datetime.now().isoformat(timespec="seconds"),
            quien,
            accion,
            registro,
            antes,
            despues,
            json.dumps(detalle or {}, ensure_ascii=False),
        )
