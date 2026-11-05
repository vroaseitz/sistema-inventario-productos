"""CA-18: los desplegables de categoria filtran lo escrito sin distinguir tildes ni mayusculas."""

import pytest

pytest.importorskip("tkinter")

from pos.interfaz.combo_filtrable import filtrar_opciones, sin_tildes  # noqa: E402

CATEGORIAS = ["Lácteos y huevos", "Té e infusiones", "Superalimentos", "Frutos secos y semillas"]


def test_sin_tildes_ignora_tildes_y_mayusculas():
    assert sin_tildes("Té VERDE") == sin_tildes("te verde") == "te verde"
    assert sin_tildes("Lácteos") == "lacteos"


def test_filtra_sin_distinguir_tildes_ni_mayusculas():
    assert filtrar_opciones(CATEGORIAS, "lacteos") == ["Lácteos y huevos"]
    # «lacteos» tambien contiene «te», pero el que EMPIEZA con lo escrito sale primero (CA-15)
    assert filtrar_opciones(CATEGORIAS, "TÉ") == ["Té e infusiones", "Lácteos y huevos"]
    assert filtrar_opciones(CATEGORIAS, "  ") == CATEGORIAS  # vacio: todas


def test_primero_las_que_empiezan_con_lo_escrito():
    assert filtrar_opciones(CATEGORIAS, "s") == [
        "Superalimentos",  # empieza con s
        "Lácteos y huevos",  # contiene "s"
        "Té e infusiones",
        "Frutos secos y semillas",
    ]


def test_sin_coincidencias_devuelve_lista_vacia():
    assert filtrar_opciones(CATEGORIAS, "zzz") == []
