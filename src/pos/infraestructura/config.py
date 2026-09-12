"""Carga de configuracion desde variables de entorno / archivo .env.

Nunca se hardcodean credenciales. Ver config/.env.example.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv es opcional en tiempo de test
    pass


@dataclass(frozen=True)
class Config:
    sqlite_path: str
    supabase_db_url: str | None

    @classmethod
    def desde_entorno(cls) -> Config:
        return cls(
            sqlite_path=os.environ.get("POS_SQLITE_PATH", "pos_local.db"),
            supabase_db_url=os.environ.get("SUPABASE_DB_URL"),
        )
