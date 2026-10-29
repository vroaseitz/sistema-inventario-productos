"""Sesion de la persona que uso el sistema (la llena el login; sin login queda el usuario 1)."""

from dataclasses import dataclass


@dataclass
class Sesion:
    usuario_id: int = 1
    nombre: str = ""
