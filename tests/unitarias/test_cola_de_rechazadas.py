"""Una operacion que la nube rechaza por sus datos se aparta con su motivo y NO frena a las demas.

Buenas practicas aplicadas a la cola: estados explicitos (pending / synced / rejected), anti-bucle
(no se reintenta eternamente lo que no sirve) y sin fallos silenciosos (se ve y se avisa).
"""

from __future__ import annotations

import pytest

from pos.aplicacion.casos_uso.sincronizar_pendientes import (
    SincronizarAlCierre,
    SincronizarPendientes,
)
from pos.aplicacion.puertos import OperacionIncompleta, OperacionRechazada
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema


class Publicador:
    """Rechaza el producto MALO; su existencia queda incompleta (el producto no llego)."""

    def __init__(self, arreglado: bool = False) -> None:
        self.publicadas: list[str] = []
        self.arreglado = arreglado

    def publicar(self, operacion: dict) -> None:
        d = operacion["datos"]
        if not self.arreglado:
            if operacion["entidad"] == "producto" and d["codigo"] == "MALO":
                raise OperacionRechazada("violates check constraint precio_venta")
            if operacion["entidad"] == "existencia" and d["codigo_producto"] == "MALO":
                raise OperacionIncompleta("existencia: esperado 1, encontrado 0")
        self.publicadas.append(operacion["id_cliente"])


@pytest.fixture
def cola(tmp_path):
    con = crear_conexion(str(tmp_path / "c.db"))
    crear_esquema(con)
    cola = ColaSincronizacionSQLite(con)
    cola.encolar("producto", "upsert", {"codigo": "BUENO1"}, "op-1")
    cola.encolar("producto", "upsert", {"codigo": "MALO"}, "op-2")
    cola.encolar("existencia", "upsert", {"codigo_producto": "MALO", "cantidad": "5"}, "op-3")
    cola.encolar("producto", "upsert", {"codigo": "BUENO2"}, "op-4")
    cola.encolar("existencia", "upsert", {"codigo_producto": "BUENO2", "cantidad": "1"}, "op-5")
    return cola


def test_un_rechazo_no_frena_al_resto_y_se_arrastra_a_lo_que_depende_de_el(cola):
    publicador = Publicador()
    resultado = SincronizarPendientes(cola, publicador).ejecutar()

    assert resultado.fallo_en is None  # la cola NO se detuvo
    assert publicador.publicadas == ["op-1", "op-4", "op-5"]  # lo demas llego completo
    assert resultado.rechazadas == 2  # el producto malo y su existencia, que depende de el
    assert cola.pendientes() == []
    rechazadas = {r["id_cliente"]: r for r in cola.rechazadas()}
    assert set(rechazadas) == {"op-2", "op-3"}
    assert "precio_venta" in rechazadas["op-2"]["motivo"]
    assert "Depende de producto MALO" in rechazadas["op-3"]["motivo"]


def test_lo_rechazado_se_reintenta_en_la_siguiente_tanda_y_pasa_si_se_arreglo(cola):
    SincronizarPendientes(cola, Publicador()).ejecutar()
    assert len(cola.rechazadas()) == 2

    arreglado = Publicador(arreglado=True)  # p. ej. se aplico la migracion 010 en la nube
    resultado = SincronizarPendientes(cola, arreglado).ejecutar()

    assert resultado.rechazadas == 0 and cola.rechazadas() == []
    assert arreglado.publicadas == ["op-2", "op-3"]  # en su orden original: producto y luego stock


def test_si_sigue_rechazada_se_aparta_otra_vez_sin_duplicarse(cola):
    for _ in range(3):
        SincronizarPendientes(cola, Publicador()).ejecutar()
    assert len(cola.rechazadas()) == 2  # siempre las mismas 2: nada se duplica ni se pierde


def test_un_fallo_de_conexion_si_detiene_la_tanda_y_no_rechaza(cola):
    class SinInternet:
        def publicar(self, operacion: dict) -> None:
            raise ConnectionError("sin internet")

    resultado = SincronizarPendientes(cola, SinInternet()).ejecutar()
    assert resultado.fallo_en == "op-1" and resultado.rechazadas == 0
    assert len(cola.pendientes()) == 5 and cola.rechazadas() == []  # nada se aparta por la red


def test_el_cierre_avisa_de_las_rechazadas_sin_decir_que_todo_salio_bien(cola):
    mensaje = SincronizarAlCierre(cola, Publicador()).ejecutar()
    assert mensaje is not None and "Jornada cerrada." in mensaje
    assert "rechazó 2 operaciones" in mensaje and "no se pierden" in mensaje
    assert "Datos enviados a la nube" not in mensaje  # no se esconde el problema
