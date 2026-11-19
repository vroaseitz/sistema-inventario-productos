"""Usuario del sistema y sus reglas (HU-USR-01)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .errores import ErrorDominio

LARGO_MINIMO_CLAVE = 8


class Rol(Enum):
    ADMIN = "admin"
    CAJERO = "cajero"


# Nombres que ven las usuarias (el prototipo habla de Administradora y Vendedora).
NOMBRES_ROL = {Rol.ADMIN: "Administradora", Rol.CAJERO: "Vendedora"}

# HU-USR-02: lo que puede hacer cada perfil, segun la tabla del prototipo v3. La vendedora
# vende y cierra caja (F1); lo demas es de la administradora.
MODULOS_POR_ROL = {
    Rol.ADMIN: frozenset({"F1", "F2", "F3", "F4", "F5", "F6", "F7"}),
    Rol.CAJERO: frozenset({"F1"}),
}


def modulos_permitidos(rol: Rol | None) -> frozenset[str]:
    """Sin rol (la app sin login, usada en pruebas y demos) se permite todo."""
    return MODULOS_POR_ROL[Rol.ADMIN] if rol is None else MODULOS_POR_ROL[rol]


class CredencialesInvalidas(ErrorDominio):
    """Usuario o clave incorrectos (mensaje unico: no revela cual de los dos fallo)."""


@dataclass
class Usuario:
    nombre: str
    clave_hash: str
    rol: Rol = Rol.CAJERO
    activo: bool = True
    id: int | None = None
    ultimo_acceso: datetime | None = None

    def __post_init__(self) -> None:
        self.nombre = self.nombre.strip().lower()
        if not self.nombre:
            raise ErrorDominio("El usuario requiere un nombre")


def validar_clave(clave: str) -> None:
    if len(clave) < LARGO_MINIMO_CLAVE:
        raise ErrorDominio(f"La clave debe tener al menos {LARGO_MINIMO_CLAVE} caracteres")
