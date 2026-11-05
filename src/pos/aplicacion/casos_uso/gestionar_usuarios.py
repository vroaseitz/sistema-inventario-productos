"""Casos de uso de usuarios y perfiles (HU-USR-01, HU-USR-02): alta, claves, perfil y estado.

Reglas: la clave tiene al menos 8 caracteres; siempre debe quedar al menos una administradora
activa; nadie se desactiva a si mismo. Cada cambio deja rastro en la auditoria (HU-USR-03). Los
mensajes de clave incorrecta no dicen si fallo el usuario o la clave.
"""

from __future__ import annotations

from dataclasses import dataclass

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.autenticar_usuario import Hasheador
from pos.aplicacion.puertos import RepositorioUsuarios
from pos.dominio.errores import ErrorDominio
from pos.dominio.usuarios import NOMBRES_ROL, CredencialesInvalidas, Rol, Usuario, validar_clave


@dataclass
class GestionarUsuarios:
    repositorio: RepositorioUsuarios
    hasheador: Hasheador
    auditor: Auditor | None = None

    def crear(self, nombre: str, clave: str, repetir: str, rol: Rol) -> Usuario:
        self._claves_iguales(clave, repetir)
        validar_clave(clave)
        usuario = Usuario(nombre, self.hasheador.hashear(clave), rol)
        if self.repositorio.obtener_por_nombre(usuario.nombre) is not None:
            raise ErrorDominio(f"Ya existe el usuario {usuario.nombre}")
        self.repositorio.guardar(usuario)
        self._auditar("Alta de usuario", usuario.nombre, "—", NOMBRES_ROL[rol])
        return usuario

    def cambiar_mi_clave(self, nombre: str, actual: str, nueva: str, repetir: str) -> None:
        usuario = self._obtener(nombre)
        if not self.hasheador.verificar(actual, usuario.clave_hash):
            raise CredencialesInvalidas("La clave actual no es correcta")
        self._claves_iguales(nueva, repetir)
        validar_clave(nueva)
        if actual == nueva:
            raise ErrorDominio("La clave nueva debe ser distinta de la actual")
        usuario.clave_hash = self.hasheador.hashear(nueva)
        self.repositorio.guardar(usuario)
        self._auditar("Cambio de contraseña", usuario.nombre, "", "cambiada")

    def restablecer_clave(self, nombre: str, nueva: str, repetir: str) -> None:
        """La administradora fija una clave nueva a otra persona (olvido de clave)."""
        usuario = self._obtener(nombre)
        self._claves_iguales(nueva, repetir)
        validar_clave(nueva)
        usuario.clave_hash = self.hasheador.hashear(nueva)
        self.repositorio.guardar(usuario)
        self._auditar("Restablecimiento de contraseña", usuario.nombre, "", "cambiada")

    def cambiar_perfil(self, nombre: str, rol: Rol) -> Usuario:
        usuario = self._obtener(nombre)
        if usuario.rol is rol:
            return usuario
        if usuario.rol is Rol.ADMIN and usuario.activo and self._admins_activos() <= 1:
            raise ErrorDominio("Debe quedar al menos una administradora activa")
        anterior = usuario.rol
        usuario.rol = rol
        self.repositorio.guardar(usuario)
        self._auditar("Cambio de perfil", usuario.nombre, NOMBRES_ROL[anterior], NOMBRES_ROL[rol])
        return usuario

    def cambiar_estado(self, nombre: str, activo: bool, quien: str = "") -> Usuario:
        usuario = self._obtener(nombre)
        if usuario.activo == activo:
            return usuario
        if not activo:
            if quien and usuario.nombre == quien.strip().lower():
                raise ErrorDominio("No puedes desactivar tu propio usuario")
            if usuario.rol is Rol.ADMIN and self._admins_activos() <= 1:
                raise ErrorDominio("Debe quedar al menos una administradora activa")
        usuario.activo = activo
        self.repositorio.guardar(usuario)
        self._auditar(
            "Activación de usuario" if activo else "Desactivación de usuario",
            usuario.nombre,
            "Inactivo" if activo else "Activo",
            "Activo" if activo else "Inactivo",
        )
        return usuario

    # ------------------------------------------------------------------ privados --

    def _obtener(self, nombre: str) -> Usuario:
        usuario = self.repositorio.obtener_por_nombre(nombre)
        if usuario is None:
            raise ErrorDominio("El usuario no existe")
        return usuario

    def _admins_activos(self) -> int:
        return sum(1 for u in self.repositorio.listar() if u.rol is Rol.ADMIN and u.activo)

    @staticmethod
    def _claves_iguales(clave: str, repetir: str) -> None:
        if clave != repetir:
            raise ErrorDominio("Las claves no coinciden")

    def _auditar(self, accion: str, registro: str, antes: str, despues: str) -> None:
        if self.auditor is not None:
            self.auditor.registrar(accion, registro, antes, despues)
