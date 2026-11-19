"""La sincronización reutiliza UNA conexión en vez de abrir una por operación."""

from __future__ import annotations

import pytest

psycopg2 = pytest.importorskip("psycopg2")

from pos.aplicacion.puertos import OperacionRechazada  # noqa: E402
from pos.infraestructura.supabase import adaptador_supabase  # noqa: E402
from pos.infraestructura.supabase.adaptador_supabase import AdaptadorSupabase  # noqa: E402


class Cursor:
    def __init__(self, conexion):
        self._c = conexion

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        if self._c.fallos:
            self._c.fallos -= 1
            raise psycopg2.OperationalError("la conexion se cerro")
        self._c.sentencias += 1

    def mogrify(self, sql, params=()):
        return sql.encode()

    def fetchone(self):
        return (1,)  # la verificacion: el dato quedo en el destino


class Conexion:
    def __init__(self, fallos=0):
        self.closed = False
        self.fallos = fallos
        self.sentencias = 0
        self.confirmadas = 0

    def __enter__(self):
        return self

    def __exit__(self, tipo, *_):
        if tipo is None:
            self.confirmadas += 1
        return False

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.closed = True


OP = {
    "entidad": "producto",
    "operacion": "upsert",
    "id_cliente": "x",
    "datos": {
        "codigo": "A",
        "nombre": "A",
        "precio": 1000,
        "unidad_venta": "unidad",
        "activo": True,
        "costo": None,
        "perecible": False,
        "dias_aviso": None,
        "stock_minimo": None,
        "categoria": None,
    },
}


@pytest.fixture
def conexiones(monkeypatch):
    abiertas: list[Conexion] = []
    plan: list[int] = []  # fallos que trae cada conexion nueva

    def conectar(*_a, **_k):
        c = Conexion(plan.pop(0) if plan else 0)
        abiertas.append(c)
        return c

    monkeypatch.setattr(psycopg2, "connect", conectar)
    monkeypatch.setattr(adaptador_supabase, "traducir_operacion", lambda op: [("SELECT 1", ())])
    return abiertas, plan


def test_mil_operaciones_usan_una_sola_conexion(conexiones):
    abiertas, _ = conexiones
    adaptador = AdaptadorSupabase("postgresql://x")
    for _ in range(1000):
        adaptador.publicar(OP)
    assert len(abiertas) == 1 and abiertas[0].confirmadas == 1000
    adaptador.cerrar()
    assert abiertas[0].closed


def test_si_el_servidor_cerro_la_conexion_inactiva_reintenta_una_vez_con_otra_nueva(conexiones):
    abiertas, plan = conexiones
    adaptador = AdaptadorSupabase("postgresql://x")
    adaptador.publicar(OP)
    abiertas[0].fallos = 1  # el servidor la cerro mientras estaba inactiva
    adaptador.publicar(OP)  # no debe fallar: reintenta con una nueva
    assert len(abiertas) == 2 and abiertas[0].closed and abiertas[1].confirmadas == 1


def test_sin_internet_en_una_conexion_nueva_falla_sin_reintentar_en_bucle(conexiones):
    abiertas, plan = conexiones
    plan.append(1)  # la conexion nueva ya falla
    adaptador = AdaptadorSupabase("postgresql://x")
    with pytest.raises(psycopg2.OperationalError):
        adaptador.publicar(OP)
    assert len(abiertas) == 1 and abiertas[0].closed


def test_un_rechazo_del_servidor_descarta_la_conexion(conexiones, monkeypatch):
    abiertas, _ = conexiones
    adaptador = AdaptadorSupabase("postgresql://x")
    adaptador.publicar(OP)

    def rechazo(*_a):
        raise psycopg2.IntegrityError("check violation")

    monkeypatch.setattr(Cursor, "execute", lambda self, *a: rechazo())
    with pytest.raises(OperacionRechazada, match="check violation"):
        adaptador.publicar(OP)
    assert abiertas[0].closed  # la siguiente operacion parte de una conexion limpia
