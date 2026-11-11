"""Hash de claves con bcrypt (la clave nunca se guarda en claro)."""

from __future__ import annotations

import bcrypt


class HasheadorBcrypt:
    def __init__(self, rondas: int = 12) -> None:
        self._rondas = rondas

    def hashear(self, clave: str) -> str:
        return bcrypt.hashpw(clave.encode(), bcrypt.gensalt(self._rondas)).decode()

    def verificar(self, clave: str, clave_hash: str) -> bool:
        try:
            return bcrypt.checkpw(clave.encode(), clave_hash.encode())
        except ValueError:  # hash corrupto o con formato ajeno
            return False
