"""Sesion de la persona que uso el sistema (la llena el login; sin login queda el usuario 1)."""

from dataclasses import dataclass

from pos.dominio.usuarios import Rol


@dataclass
class Sesion:
    usuario_id: int = 1
    nombre: str = ""
    rol: Rol | None = None  # sin login queda en None y se permite todo
