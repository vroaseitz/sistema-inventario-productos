"""Adaptador de publicacion hacia Supabase (PostgreSQL). Implementa PublicadorRemoto.

REQUIERE ENTORNO REAL: credenciales de Supabase (SUPABASE_DB_URL) y conectividad.
No se puede ejecutar ni testear de extremo a extremo sin esas credenciales; por eso
los tests usan un doble en memoria de PublicadorRemoto. Aqui queda la implementacion
real, lista para conectarse.

Notas de conexion (ver docs/08-diseno/adr/0001):
- Usar el POOLER de Supabase, no el puerto 5432 directo (Supabase deprecio IPv4 directo).
  Session mode: 5432 ; Transaction mode: 6543.
- psycopg2-binary trae su propio libpq + OpenSSL, por lo que el TLS 1.2 NO depende del
  SChannel de Windows 8.1 (ventaja del stack Python para el equipo viejo del local).
- La operacion se aplica a las TABLAS DE NEGOCIO (productos, existencias) con sentencias
  idempotentes (ON CONFLICT sobre la clave de negocio); el mapeo vive en `traductor.py`.
"""

from __future__ import annotations

from typing import Any

from pos.infraestructura.supabase.traductor import traducir_operacion


class AdaptadorSupabase:
    """Publica operaciones en PostgreSQL/Supabase usando psycopg2.

    La importacion de psycopg2 es perezosa para que el resto del sistema (y los tests)
    no dependan de tenerlo instalado ni de credenciales.
    """

    def __init__(self, db_url: str) -> None:
        if not db_url:
            raise ValueError("Se requiere SUPABASE_DB_URL para el adaptador Supabase")
        self._db_url = db_url

    def _conectar(self) -> Any:
        try:
            import psycopg2  # noqa: PLC0415 (import perezoso intencional)
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "psycopg2-binary no esta instalado (pip install psycopg2-binary)"
            ) from exc
        # sslmode=require fuerza TLS hacia Supabase.
        return psycopg2.connect(self._db_url, sslmode="require")

    def publicar(self, operacion: dict) -> None:  # pragma: no cover - requiere credenciales
        # El mapeo entidad -> sentencia (testeado en test_traductor_supabase) se resuelve
        # antes de abrir la conexion, para fallar rapido ante una entidad no soportada.
        sql, params = traducir_operacion(operacion)
        conexion = self._conectar()
        try:
            with conexion, conexion.cursor() as cur:
                cur.execute(sql, params)
        finally:
            conexion.close()
