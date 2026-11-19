"""SY-01: al cerrar la jornada se envía lo pendiente a la nube sin bloquear el cierre."""

from __future__ import annotations

import pytest

from pos.aplicacion.casos_uso.sincronizar_pendientes import (
    MENSAJE_CIERRE_ENVIADO,
    SincronizarAlCierre,
)
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema


class PublicadorQueAcepta:
    def __init__(self) -> None:
        self.publicadas: list[str] = []

    def publicar(self, operacion: dict) -> None:
        self.publicadas.append(operacion["id_cliente"])


class PublicadorSinInternet:
    def publicar(self, operacion: dict) -> None:
        raise ConnectionError("sin internet")


class PublicadorQueSeCorta(PublicadorQueAcepta):
    def __init__(self, acepta: int) -> None:
        super().__init__()
        self._acepta = acepta

    def publicar(self, operacion: dict) -> None:
        if len(self.publicadas) >= self._acepta:
            raise ConnectionError("se corto")
        super().publicar(operacion)


@pytest.fixture
def cola(tmp_path):
    con = crear_conexion(str(tmp_path / "c.db"))
    crear_esquema(con)
    cola = ColaSincronizacionSQLite(con)
    for i in range(3):
        cola.encolar("producto", "upsert", {"codigo": f"P{i}"}, f"op-{i}")
    return cola


def test_con_internet_vacia_la_cola_y_avisa(cola):
    publicador = PublicadorQueAcepta()
    mensaje = SincronizarAlCierre(cola, publicador).ejecutar()
    assert mensaje == MENSAJE_CIERRE_ENVIADO
    assert cola.pendientes() == [] and len(publicador.publicadas) == 3


def test_sin_internet_deja_todo_pendiente_y_avisa_cuantas(cola):
    mensaje = SincronizarAlCierre(cola, PublicadorSinInternet()).ejecutar()
    assert mensaje is not None and "Quedan 3 operaciones sin enviar" in mensaje
    assert "próximo cierre" in mensaje and "Sincronizar" in mensaje
    assert len(cola.pendientes()) == 3


def test_corte_a_mitad_marca_lo_enviado_y_no_duplica(cola):
    publicador = PublicadorQueSeCorta(acepta=1)
    mensaje = SincronizarAlCierre(cola, publicador).ejecutar()
    assert mensaje is not None and "Quedan 2 operaciones" in mensaje
    assert len(publicador.publicadas) == 1
    # el siguiente cierre envia solo lo que falta
    siguiente = PublicadorQueAcepta()
    assert SincronizarAlCierre(cola, siguiente).ejecutar() == MENSAJE_CIERRE_ENVIADO
    assert len(siguiente.publicadas) == 2


def test_sin_supabase_no_hace_nada_ni_muestra_error(cola):
    assert SincronizarAlCierre(cola, None).ejecutar() is None
    assert SincronizarAlCierre(None, PublicadorQueAcepta()).ejecutar() is None
    assert len(cola.pendientes()) == 3


def test_un_error_inesperado_nunca_rompe_el_cierre():
    class ColaRota:
        def pendientes(self):
            raise RuntimeError("base bloqueada")

    assert SincronizarAlCierre(ColaRota(), PublicadorQueAcepta()).ejecutar() is None


def test_al_cierre_se_envia_solo_lo_que_alcanza_en_el_tiempo_dado(cola):
    """Tras una migracion hay miles de pendientes: el cierre no se queda esperando minutos."""
    tiempo = [0.0]

    class Lento(PublicadorQueAcepta):
        def publicar(self, operacion: dict) -> None:
            tiempo[0] += 1.0  # cada envio «tarda» 1 segundo
            super().publicar(operacion)

    publicador = Lento()
    mensaje = SincronizarAlCierre(
        cola, publicador, limite_segundos=2.0, reloj=lambda: tiempo[0]
    ).ejecutar()
    assert len(publicador.publicadas) == 2  # alcanzo para 2 de las 3
    assert mensaje is not None and "Quedan 1 operaciones sin enviar" in mensaje
    assert len(cola.pendientes()) == 1  # lo que falta sigue pendiente, sin perderse


def test_la_tanda_cierra_la_conexion_del_publicador_al_terminar(cola):
    class ConConexion(PublicadorQueAcepta):
        cerrada = 0

        def cerrar(self) -> None:
            self.cerrada += 1

    publicador = ConConexion()
    SincronizarAlCierre(cola, publicador).ejecutar()
    assert publicador.cerrada == 1
