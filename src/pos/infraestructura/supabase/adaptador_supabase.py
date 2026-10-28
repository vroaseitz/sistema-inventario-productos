"""Adaptador de publicacion hacia Supabase (PostgreSQL). Implementa PublicadorRemoto.

Se prueba contra un PostgreSQL real con tests/integracion/test_sync_postgres.py
(variable POS_TEST_PG_URL); sin ella esos tests se omiten.

Notas de conexion (ver docs/08-diseno/adr/0001):
- Usar el POOLER de Supabase, no el puerto 5432 directo (Supabase deprecio IPv4 directo).
  Session mode: 5432 ; Transaction mode: 6543.
- psycopg2-binary trae su propio libpq + OpenSSL, por lo que el TLS 1.2 NO depende del
  SChannel de Windows 8.1 (ventaja del stack Python para el equipo viejo del local).
- La operacion se aplica a las TABLAS DE NEGOCIO del schema `pos` con sentencias
  idempotentes (ON CONFLICT); el mapeo vive en `traductor.py`.
"""

from __future__ import annotations

from typing import Any

from pos.infraestructura.supabase.traductor import traducir_operacion


class AdaptadorSupabase:
    """Publica operaciones en PostgreSQL/Supabase usando psycopg2.

    La importacion de psycopg2 es perezosa para que el resto del sistema (y los tests)
    no dependan de tenerlo instalado ni de credenciales.
    """

    def __init__(self, db_url: str, sslmode: str = "require") -> None:
        if not db_url:
            raise ValueError("Se requiere SUPABASE_DB_URL para el adaptador Supabase")
        self._db_url = db_url
        # "require" fuerza TLS hacia Supabase; solo las pruebas locales usan "disable".
        self._sslmode = sslmode

    def _conectar(self) -> Any:
        try:
            import psycopg2  # noqa: PLC0415 (import perezoso intencional)
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "psycopg2-binary no esta instalado (pip install psycopg2-binary)"
            ) from exc
        # Si la URL ya trae sslmode, manda la URL (p. ej. ?sslmode=disable en pruebas locales).
        extra = {} if "sslmode=" in self._db_url else {"sslmode": self._sslmode}
        return psycopg2.connect(self._db_url, connect_timeout=5, **extra)

    def publicar(self, operacion: dict) -> None:
        # El mapeo entidad -> sentencias (testeado en test_traductor_supabase) se resuelve
        # antes de abrir la conexion, para fallar rapido ante una entidad no soportada.
        sentencias = traducir_operacion(operacion)
        conexion = self._conectar()
        try:
            # `with conexion` = una transaccion: todas las sentencias o ninguna.
            with conexion, conexion.cursor() as cur:
                for sql, params in sentencias:
                    cur.execute(sql, params)
                verificar_efecto(cur, operacion)
        finally:
            conexion.close()


def verificar_efecto(cur: Any, operacion: dict) -> None:
    """Falla si la operacion no dejo su efecto en la base remota.

    `ON CONFLICT DO NOTHING` y los `INSERT ... SELECT` terminan sin error aunque no
    inserten nada (p. ej. un turno o un producto que todavia no llego). Si eso pasara,
    la cola la marcaria como sincronizada y el dato se perderia en silencio: aqui se
    convierte en un error para que quede pendiente y se reintente en orden.
    """
    entidad, d = operacion["entidad"], operacion["datos"]

    if entidad == "producto":
        cur.execute("SELECT count(*) FROM pos.producto WHERE codigo = %s", (d["codigo"],))
        esperado = 1
    elif entidad == "existencia":
        cur.execute(
            "SELECT count(*) FROM pos.existencia e JOIN pos.producto p ON p.id = e.producto_id "
            "WHERE p.codigo = %s",
            (d["codigo_producto"],),
        )
        esperado = 1
    elif entidad == "turno_abrir":
        cur.execute("SELECT count(*) FROM pos.turno_caja WHERE id_cliente = %s", (d["uuid"],))
        esperado = 1
    elif entidad == "turno_cerrar":
        cur.execute(
            "SELECT count(*) FROM pos.turno_caja WHERE id_cliente = %s AND cerrado_en IS NOT NULL",
            (d["uuid"],),
        )
        esperado = 1
    elif entidad == "movimiento_caja":
        cur.execute(
            "SELECT count(*) FROM pos.movimiento_caja WHERE id_cliente = %s",
            (operacion["id_cliente"],),
        )
        esperado = 1
    elif entidad == "venta":
        cur.execute(
            "SELECT count(*) FROM pos.venta_detalle d JOIN pos.venta v ON v.id = d.venta_id "
            "WHERE v.id_cliente = %s",
            (d["uuid"],),
        )
        esperado = len(d["detalles"])
    else:
        return

    (encontrado,) = cur.fetchone()
    if encontrado != esperado:
        raise RuntimeError(
            f"La operacion {entidad} no quedo completa en el destino "
            f"(esperado {esperado}, encontrado {encontrado}); queda pendiente"
        )
