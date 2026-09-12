"""Pruebas de la cola de sincronizacion offline y del caso de uso de sincronizacion.

Incluye el escenario critico del premortem: un corte a mitad de la sincronizacion no
debe perder ni duplicar datos.
"""

import pytest

from pos.aplicacion.casos_uso.sincronizar_pendientes import SincronizarPendientes
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema


@pytest.fixture
def cola():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    yield ColaSincronizacionSQLite(con)
    con.close()


class PublicadorEnMemoria:
    """Doble de PublicadorRemoto que registra lo publicado (idempotente por id)."""

    def __init__(self):
        self.publicados: dict[str, dict] = {}

    def publicar(self, operacion):
        self.publicados[operacion["id_cliente"]] = operacion


class PublicadorQueFallaEn:
    """Publica bien hasta que ve cierto id_cliente, donde lanza una excepcion."""

    def __init__(self, id_que_falla):
        self.id_que_falla = id_que_falla
        self.publicados: dict[str, dict] = {}

    def publicar(self, operacion):
        if operacion["id_cliente"] == self.id_que_falla:
            raise ConnectionError("cayo la red a mitad de la sincronizacion")
        self.publicados[operacion["id_cliente"]] = operacion


def test_encolar_es_idempotente(cola):
    cola.encolar("producto", "crear", {"codigo": "1"}, id_cliente="uuid-1")
    cola.encolar("producto", "crear", {"codigo": "1"}, id_cliente="uuid-1")  # reintento
    assert len(cola.pendientes()) == 1


def test_sincroniza_todas_las_pendientes(cola):
    cola.encolar("producto", "crear", {"codigo": "1"}, "uuid-1")
    cola.encolar("producto", "crear", {"codigo": "2"}, "uuid-2")
    pub = PublicadorEnMemoria()

    resultado = SincronizarPendientes(cola, pub).ejecutar()

    assert resultado.sincronizadas == 2
    assert cola.pendientes() == []
    assert set(pub.publicados) == {"uuid-1", "uuid-2"}


def test_corte_a_mitad_no_pierde_ni_duplica(cola):
    # Escenario del premortem: se cae la red al procesar la 2.a operacion.
    cola.encolar("producto", "crear", {"codigo": "1"}, "uuid-1")
    cola.encolar("producto", "crear", {"codigo": "2"}, "uuid-2")
    cola.encolar("producto", "crear", {"codigo": "3"}, "uuid-3")

    pub_falla = PublicadorQueFallaEn("uuid-2")
    r1 = SincronizarPendientes(cola, pub_falla).ejecutar()

    # La 1.a quedo sincronizada; se detuvo en la 2.a.
    assert r1.sincronizadas == 1
    assert r1.fallo_en == "uuid-2"
    ids_pendientes = {op["id_cliente"] for op in cola.pendientes()}
    assert ids_pendientes == {"uuid-2", "uuid-3"}  # nada se perdio

    # Se restablece la red y se reintenta: solo procesa lo pendiente, sin duplicar.
    pub_ok = PublicadorEnMemoria()
    r2 = SincronizarPendientes(cola, pub_ok).ejecutar()
    assert r2.sincronizadas == 2
    assert set(pub_ok.publicados) == {"uuid-2", "uuid-3"}  # uuid-1 no se reenvia
    assert cola.pendientes() == []
