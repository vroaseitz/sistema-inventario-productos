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


# --- CA-18 (QA 09-11): la lista se despliega y se acorta con cada letra ---------------------------


def _combo_con_pantalla():
    tk = pytest.importorskip("tkinter")
    from pos.interfaz.combo_filtrable import ComboFiltrable

    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin entorno grafico")
    variable = tk.StringVar(value="Todas")
    combo = ComboFiltrable(raiz, variable, ["Todas", "Lácteos", "Frutos secos", "Té y hierbas"])
    combo.pack()
    raiz.update()
    return raiz, combo, variable


class _Tecla:
    keysym = "a"


def test_al_escribir_se_despliega_una_lista_que_se_acorta():
    raiz, combo, variable = _combo_con_pantalla()
    try:
        variable.set("lac")
        combo._al_escribir(_Tecla())
        assert combo._popup is not None  # la lista se despliega sin presionar Enter
        assert combo._lista.get(0, "end") == ("Lácteos",)  # sin distinguir tildes ni mayusculas
        variable.set("t")
        combo._al_escribir(_Tecla())
        assert combo._lista.get(0, "end")[:2] == (
            "Todas",
            "Té y hierbas",
        )  # primero las que empiezan igual
    finally:
        raiz.destroy()


def test_enter_elige_la_primera_opcion_que_queda_y_cierra_la_lista():
    raiz, combo, variable = _combo_con_pantalla()
    try:
        variable.set("fru")
        combo._al_escribir(_Tecla())
        combo._al_enter()
        assert variable.get() == "Frutos secos"
        assert combo._popup is None
    finally:
        raiz.destroy()


def test_las_flechas_recorren_la_lista_y_enter_elige_la_resaltada():
    raiz, combo, variable = _combo_con_pantalla()
    try:
        variable.set("s")  # «Frutos secos», «Té y hierbas», «Lácteos»... contienen «s»
        combo._al_escribir(_Tecla())
        opciones = combo._lista.get(0, "end")
        assert len(opciones) >= 2
        assert combo._mover(1) == "break"
        combo._al_enter()
        assert variable.get() == opciones[1]
    finally:
        raiz.destroy()


def test_sin_texto_o_sin_coincidencias_no_hay_lista():
    raiz, combo, variable = _combo_con_pantalla()
    try:
        variable.set("zzz")
        combo._al_escribir(_Tecla())
        assert combo._popup is None
        variable.set("")
        combo._al_escribir(_Tecla())
        assert combo._popup is None
    finally:
        raiz.destroy()
