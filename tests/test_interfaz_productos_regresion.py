"""Pruebas de regresion QA para la interfaz Tkinter de productos.

Cubre los hallazgos QA:
- QA C-06: margen/markup muestran "falta costo" con costo vacio o 0 (no "100%").
- QA C-08a/b: busqueda normalizada (quita tildes, minusculas) y ejecutada con Enter.
- QA C-11: `_limpiar_formulario` resetea todos los campos y devuelve el foco.

Las pruebas no abren ventanas reales: se crea la instancia con `__new__` (sin
ejecutar `__init__` ni Tk) y los widgets/variables son MagicMocks, para que
corran headless y rapido en la terminal.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("tkinter", reason="Tkinter no disponible en este entorno")

from pos.dominio.categorias import Categoria
from pos.interfaz.app_tkinter import VentanaProductos, _normalizar


@pytest.fixture
def vista() -> VentanaProductos:
    """Instancia 'vacia' de la vista: sin Tk real, solo atributos simulados."""
    v = VentanaProductos.__new__(VentanaProductos)

    # Variables reactivas
    v._precio_var = MagicMock(name="precio_var")
    v._costo_var = MagicMock(name="costo_var")
    v._margen_var = MagicMock(name="margen_var")
    v._markup_var = MagicMock(name="markup_var")

    # Widgets
    v._entradas = {
        "codigo": MagicMock(name="entry_codigo"),
        "nombre": MagicMock(name="entry_nombre"),
        "precio": MagicMock(name="entry_precio"),
    }
    v._dias_aviso = MagicMock(name="entry_dias_aviso")
    v._categoria = MagicMock(name="combobox_categoria")
    v._granel = MagicMock(name="var_granel")
    v._perecible = MagicMock(name="var_perecible")
    v._entrada_busqueda = MagicMock(name="entry_busqueda")
    v._tabla = MagicMock(name="treeview")

    # Colaboradores
    v._repo = MagicMock(name="repo")
    v._registrar = MagicMock(name="registrar")
    v._editar = MagicMock(name="editar")

    return v


# --- QA C-06: indicadores con costo faltante o cero ----------------------------


class TestIndicadoresCosto:
    def test_costo_vacio_muestra_falta_costo(self, vista):
        vista._costo_var.get.return_value = "  "

        vista._actualizar_indicadores()

        vista._margen_var.set.assert_called_once_with("falta costo")
        vista._markup_var.set.assert_called_once_with("falta costo")

    def test_costo_cero_muestra_falta_costo_y_no_100(self, vista):
        vista._costo_var.get.return_value = "0"
        vista._precio_var.get.return_value = "2000"

        vista._actualizar_indicadores()

        # QA C-06: ni Margen ni Markup deben mostrar 100% con costo 0.
        texto_margen = vista._margen_var.set.call_args.args[0]
        texto_markup = vista._markup_var.set.call_args.args[0]
        assert texto_margen == "falta costo"
        assert texto_markup == "falta costo"
        assert "100%" not in texto_margen
        assert "100%" not in texto_markup

    def test_costo_none_muestra_falta_costo(self, vista):
        # Producto con costo None: producto.margen y producto.markup son None.
        from pos.dominio.productos import Producto
        from pos.dominio.value_objects import Dinero

        vista._costo_var.get.return_value = ""
        vista._precio_var.get.return_value = "2000"

        producto = Producto(codigo="X", nombre="X", precio=Dinero(2000), categoria_id=1)
        assert producto.margen is None
        assert producto.markup is None

        vista._actualizar_indicadores()

        vista._margen_var.set.assert_called_once_with("falta costo")
        vista._markup_var.set.assert_called_once_with("falta costo")

    def test_costo_valido_calcula_porcentajes(self, vista):
        vista._costo_var.get.return_value = "1000"
        vista._precio_var.get.return_value = "2000"

        vista._actualizar_indicadores()

        assert vista._margen_var.set.call_args.args[0] == "50.0%"
        assert vista._markup_var.set.call_args.args[0] == "100.0%"


class TestColumnaCategoria:
    def test_tabla_muestra_nombre_categoria_no_id(self, vista):
        """QA C-02: la columna Categoría muestra texto ("Abarrotes"), no el id numerico."""
        from pos.dominio.productos import Producto
        from pos.dominio.value_objects import Dinero

        producto = Producto(codigo="C-9", nombre="Quinoa", precio=Dinero(3000), categoria_id=3)
        vista._repo.listar.return_value = [producto]
        vista._tabla.get_children.return_value = []

        vista._refrescar()

        valores = vista._tabla.insert.call_args.kwargs["values"]
        assert valores[4] == "abarrotes"
        assert not isinstance(valores[4], int)


class TestComboboxCategoriasDinamicas:
    """C-02/C-04: el combobox de categorias se alimenta de la BD, no de una tupla fijada."""

    def test_combo_se_llena_desde_bd(self, vista):
        # La GUI pide listar_categorias() al repositorio (contrato nuevo).
        vista._repo.listar_categorias.return_value = [
            Categoria(id=1, nombre="frutas"),
            Categoria(id=2, nombre="verduras"),
            Categoria(id=9, nombre="panaderia"),
        ]

        # Reproducimos la carga de categorias tal como la hace _construir.
        from pos.interfaz.app_tkinter import _cargar_nombres_categorias

        nombres = _cargar_nombres_categorias(vista._repo)

        assert nombres == ["frutas", "verduras", "panaderia"]
        vista._repo.listar_categorias.assert_called_once()


# --- QA C-08a/b: busqueda normalizada y disparada con Enter --------------------


class TestBusqueda:
    def test_normalizar_quita_tildes_y_pasa_a_minusculas(self):
        assert _normalizar("Café de Grano") == "cafe de grano"
        assert _normalizar("ÁRBOL") == "arbol"
        assert _normalizar("MÍEL") == "miel"

    def test_busqueda_con_termino_sin_tilde_encuentra_producto_con_tilde(self, vista):
        from pos.dominio.productos import Producto
        from pos.dominio.value_objects import Dinero

        cafe = Producto(codigo="C-001", nombre="Café de grano", precio=Dinero(5000), categoria_id=1)
        arroz = Producto(codigo="A-001", nombre="Arroz", precio=Dinero(1000), categoria_id=1)
        vista._repo.listar.return_value = [cafe, arroz]
        vista._tabla.get_children.return_value = []
        vista._entrada_busqueda.get.return_value = "cafe"

        vista._ejecutar_busqueda()

        vista._tabla.insert.assert_called_once()
        valores = vista._tabla.insert.call_args.kwargs["values"]
        assert valores[1] == "Café de grano"

    def test_busqueda_por_codigo_exacto(self, vista):
        from pos.dominio.productos import Producto
        from pos.dominio.value_objects import Dinero

        cafe = Producto(codigo="C-001", nombre="Café de grano", precio=Dinero(5000), categoria_id=1)
        vista._repo.listar.return_value = [cafe]
        vista._tabla.get_children.return_value = []
        vista._entrada_busqueda.get.return_value = "c-001"

        vista._ejecutar_busqueda()

        vista._tabla.insert.assert_called_once()

    def test_busqueda_vacia_refresca_listado_completo(self, vista):
        vista._entrada_busqueda.get.return_value = ""
        vista._refrescar = MagicMock(name="refrescar")

        vista._ejecutar_busqueda()

        vista._refrescar.assert_called_once()


# --- QA C-11: limpieza de formulario y foco ------------------------------------


class TestLimpiarFormulario:
    def test_resetea_todos_los_campos_y_enfoca_codigo(self, vista):
        vista._limpiar_formulario()

        vista._entradas["codigo"].delete.assert_called_once()
        vista._entradas["nombre"].delete.assert_called_once()
        vista._entradas["precio"].delete.assert_called_once()
        vista._dias_aviso.delete.assert_called_once()
        vista._costo_var.set.assert_called_once_with("")
        vista._categoria.set.assert_called_once_with("")
        vista._granel.set.assert_called_once_with(False)
        vista._perecible.set.assert_called_once_with(False)
        vista._margen_var.set.assert_called_once_with("Sin dato")
        vista._markup_var.set.assert_called_once_with("Sin dato")
        vista._entradas["codigo"].focus_set.assert_called_once()


class TestCancelarEdicion:
    def test_boton_cancelar_sale_de_modo_edicion(self, vista):
        # Simular modo edicion: boton "Guardar cambios" y codigo deshabilitado.
        vista._boton_guardar = MagicMock(name="boton_guardar")
        vista._producto_en_edicion = "P-200"

        vista._cancelar_edicion()

        # El formulario se limpia, el codigo se re-habilita y el boton
        # vuelve al modo alta.
        vista._entradas["codigo"].config.assert_called_once_with(state="normal")
        vista._boton_guardar.config.assert_called_once_with(text="Agregar")
        assert vista._producto_en_edicion is None
        vista._costo_var.set.assert_called_with("")
        vista._margen_var.set.assert_called_with("Sin dato")
        vista._entradas["codigo"].focus_set.assert_called_once()
