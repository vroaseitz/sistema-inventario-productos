"""Casos de uso de acceso: crear usuario y autenticar (HU-USR-01)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pos.aplicacion.puertos import RepositorioUsuarios
from pos.dominio.errores import ErrorDominio
from pos.dominio.usuarios import CredencialesInvalidas, Rol, Usuario, validar_clave


class Hasheador(Protocol):
    def hashear(self, clave: str) -> str: ...
    def verificar(self, clave: str, clave_hash: str) -> bool: ...


@dataclass
class CrearUsuario:
    repositorio: RepositorioUsuarios
    hasheador: Hasheador

    def ejecutar(self, nombre: str, clave: str, rol: Rol = Rol.CAJERO) -> Usuario:
        validar_clave(clave)
        usuario = Usuario(nombre, self.hasheador.hashear(clave), rol)
        if self.repositorio.obtener_por_nombre(usuario.nombre) is not None:
            raise ErrorDominio(f"Ya existe el usuario {usuario.nombre}")
        self.repositorio.guardar(usuario)
        return usuario


@dataclass
class AutenticarUsuario:
    repositorio: RepositorioUsuarios
    hasheador: Hasheador

    def ejecutar(self, nombre: str, clave: str) -> Usuario:
        usuario = self.repositorio.obtener_por_nombre(nombre)
        # Mismo error si el usuario no existe, esta inactivo o la clave no coincide.
        if usuario is None or not usuario.activo:
            raise CredencialesInvalidas("Usuario o clave incorrectos")
        if not self.hasheador.verificar(clave, usuario.clave_hash):
            raise CredencialesInvalidas("Usuario o clave incorrectos")
        return usuario
