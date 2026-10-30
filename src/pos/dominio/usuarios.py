"""Usuario del sistema y sus reglas (HU-USR-01)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errores import ErrorDominio

LARGO_MINIMO_CLAVE = 8


class Rol(Enum):
    ADMIN = "admin"
    CAJERO = "cajero"


class CredencialesInvalidas(ErrorDominio):
    """Usuario o clave incorrectos (mensaje unico: no revela cual de los dos fallo)."""


@dataclass
class Usuario:
    nombre: str
    clave_hash: str
    rol: Rol = Rol.CAJERO
    activo: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        self.nombre = self.nombre.strip().lower()
        if not self.nombre:
            raise ErrorDominio("El usuario requiere un nombre")


def validar_clave(clave: str) -> None:
    if len(clave) < LARGO_MINIMO_CLAVE:
        raise ErrorDominio(f"La clave debe tener al menos {LARGO_MINIMO_CLAVE} caracteres")
