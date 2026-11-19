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

import contextlib
from typing import Any

from pos.aplicacion.puertos import OperacionIncompleta, OperacionRechazada
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
        # Una sola conexion para toda la tanda: abrir una por operacion (TCP + TLS + login) era lo
        # que hacia lenta la primera sincronizacion tras una migracion (miles de operaciones).
        self._conexion: Any = None

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

    def cerrar(self) -> None:
        """Cierra la conexion reutilizada al terminar la tanda; la proxima abre otra."""
        conexion, self._conexion = self._conexion, None
        if conexion is not None:
            with contextlib.suppress(Exception):  # una conexion rota no debe romper el cierre
                conexion.close()

    def _conexion_viva(self) -> tuple[Any, bool]:
        """(conexion, era_reutilizada). Abre una nueva si no hay o si el servidor la cerro."""
        actual = self._conexion
        if actual is not None and not actual.closed:
            return actual, True
        self._conexion = self._conectar()
        return self._conexion, False

    def publicar(self, operacion: dict) -> None:
        # El mapeo entidad -> sentencias (testeado en test_traductor_supabase) se resuelve
        # antes de abrir la conexion, para fallar rapido ante una entidad no soportada.
        sentencias = traducir_operacion(operacion)
        import psycopg2  # noqa: PLC0415 (import perezoso intencional)

        conexion, reutilizada = self._conexion_viva()
        try:
            self._aplicar(conexion, sentencias, operacion)
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            # La conexion pudo cortarse mientras estaba inactiva (el servidor la cierra): se
            # descarta y, si era una reutilizada, se reintenta UNA vez con una nueva.
            self.cerrar()
            if not reutilizada:
                raise
            conexion, _ = self._conexion_viva()
            try:
                self._aplicar(conexion, sentencias, operacion)
            except (psycopg2.IntegrityError, psycopg2.DataError) as exc:
                self.cerrar()
                motivo = (str(exc).strip().splitlines() or [type(exc).__name__])[0]
                raise OperacionRechazada(motivo) from exc
            except Exception:
                self.cerrar()
                raise
        except (psycopg2.IntegrityError, psycopg2.DataError) as exc:
            # El destino rechazo los DATOS (restriccion, tipo, duplicado): no es la conexion y
            # reintentar no sirve. Se avisa con un error propio para apartarla sin frenar la cola.
            self.cerrar()
            motivo = (str(exc).strip().splitlines() or [type(exc).__name__])[0]
            raise OperacionRechazada(motivo) from exc
        except Exception:
            self.cerrar()  # tras un rechazo del servidor la siguiente operacion parte limpia
            raise

    @staticmethod
    def _aplicar(conexion: Any, sentencias: list, operacion: dict) -> None:
        # `with conexion` = una transaccion: todas las sentencias o ninguna (y no cierra).
        with conexion, conexion.cursor() as cur:
            verificacion = consulta_de_verificacion(operacion)
            todas = [*sentencias, *([verificacion[:2]] if verificacion else [])]
            # Las sentencias de la operacion y su verificacion viajan JUNTAS: una sola ida y
            # vuelta al servidor en vez de una por sentencia (con la nube, ~100 ms cada una).
            textos = (cur.mogrify(sql, params).decode() for sql, params in todas)
            cur.execute(";\n".join(textos))
            if verificacion:
                comprobar(operacion, cur.fetchone()[0], verificacion[2])


def consulta_de_verificacion(operacion: dict) -> tuple[str, tuple, int] | None:
    """Consulta que comprueba que la operacion dejo su efecto en la base remota, o None.

    `ON CONFLICT DO NOTHING` y los `INSERT ... SELECT` terminan sin error aunque no
    inserten nada (p. ej. un turno o un producto que todavia no llego). Si eso pasara,
    la cola la marcaria como sincronizada y el dato se perderia en silencio: la comprobacion
    lo convierte en un error para que quede pendiente y se reintente en orden.
    Devuelve (sql, parametros, filas_esperadas).
    """
    entidad, d = operacion["entidad"], operacion["datos"]

    if entidad == "producto":
        return ("SELECT count(*) FROM pos.producto WHERE codigo = %s", (d["codigo"],), 1)
    if entidad == "existencia":
        return (
            "SELECT count(*) FROM pos.existencia e JOIN pos.producto p ON p.id = e.producto_id "
            "WHERE p.codigo = %s",
            (d["codigo_producto"],),
            1,
        )
    if entidad == "lote":
        return ("SELECT count(*) FROM pos.lote WHERE id_cliente = %s", (d["uuid"],), 1)
    if entidad == "turno_abrir":
        return ("SELECT count(*) FROM pos.turno_caja WHERE id_cliente = %s", (d["uuid"],), 1)
    if entidad == "turno_cerrar":
        return (
            "SELECT count(*) FROM pos.turno_caja WHERE id_cliente = %s AND cerrado_en IS NOT NULL",
            (d["uuid"],),
            1,
        )
    if entidad == "movimiento_caja":
        return (
            "SELECT count(*) FROM pos.movimiento_caja WHERE id_cliente = %s",
            (operacion["id_cliente"],),
            1,
        )
    if entidad == "venta":
        return (
            "SELECT count(*) FROM pos.venta_detalle d JOIN pos.venta v ON v.id = d.venta_id "
            "WHERE v.id_cliente = %s",
            (d["uuid"],),
            len(d["detalles"]),
        )
    return None


def comprobar(operacion: dict, encontrado: int, esperado: int) -> None:
    if encontrado != esperado:
        raise OperacionIncompleta(
            f"La operacion {operacion['entidad']} no quedo completa en el destino "
            f"(esperado {esperado}, encontrado {encontrado}); queda pendiente"
        )
