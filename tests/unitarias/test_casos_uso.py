"""Pruebas de los casos de uso con dobles en memoria (sin infraestructura real).

Demuestran que los casos de uso dependen de los PUERTOS y no de SQLite/Supabase:
aqui se inyectan repositorios falsos en memoria.
"""

from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.ajustar_stock import AjustarStock
from pos.aplicacion.casos_uso.escanear_codigo import EscanearCodigo
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.dominio.codigo_barras import calcular_digito_verificador
from pos.dominio.errores import (
    CodigoBarrasInvalido,
    DatosProductoInvalidos,
    ReglaInventarioInvalida,
)
from pos.dominio.inventario import Existencia
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Dinero


class RepoProductosMemoria:
    def __init__(self):
        self._datos: dict[str, Producto] = {}

    def guardar(self, producto):
        self._datos[producto.codigo] = producto

    def obtener_por_codigo(self, codigo):
        return self._datos.get(codigo)

    def listar(self):
        return list(self._datos.values())


class RepoExistenciasMemoria:
    def __init__(self):
        self._datos: dict[str, Existencia] = {}

    def obtener(self, codigo_producto):
        return self._datos.get(codigo_producto)

    def guardar(self, existencia):
        self._datos[existencia.codigo_producto] = existencia


def ean13(doce: str) -> str:
    return doce + str(calcular_digito_verificador(doce))


# --- RegistrarProducto --------------------------------------------------------


def test_registrar_producto_ok():
    repo = RepoProductosMemoria()
    caso = RegistrarProducto(repo)
    p = caso.ejecutar("12345", "Nueces", 8000, UnidadVenta.GRANEL, "Frutos secos")
    assert repo.obtener_por_codigo("12345") is p
    assert p.es_granel is True


def test_registrar_producto_duplicado_falla():
    repo = RepoProductosMemoria()
    caso = RegistrarProducto(repo)
    caso.ejecutar("12345", "Nueces", 8000)
    with pytest.raises(DatosProductoInvalidos):
        caso.ejecutar("12345", "Otro", 100)


# --- EscanearCodigo -----------------------------------------------------------


def test_escanear_codigo_granel_calcula_total_por_peso():
    repo = RepoProductosMemoria()
    repo.guardar(Producto("12345", "Nueces", Dinero(8000), unidad_venta=UnidadVenta.GRANEL))
    caso = EscanearCodigo(repo)
    linea = caso.ejecutar(ean13("201234501500"))  # 1.5 kg
    assert linea.cantidad == Decimal("1.500")
    assert linea.total.monto == 12000


def test_escanear_codigo_producto_inexistente():
    caso = EscanearCodigo(RepoProductosMemoria())
    with pytest.raises(CodigoBarrasInvalido):
        caso.ejecutar(ean13("201234501500"))


# --- AjustarStock -------------------------------------------------------------


def test_ajustar_stock_ingreso_y_descuento():
    repo = RepoExistenciasMemoria()
    caso = AjustarStock(repo)
    caso.ingresar("12345", Decimal("10"))
    e = caso.descontar("12345", Decimal("3"))
    assert e.cantidad == Decimal("7")


def test_descontar_sin_existencia_falla():
    caso = AjustarStock(RepoExistenciasMemoria())
    with pytest.raises(ReglaInventarioInvalida):
        caso.descontar("nope", Decimal("1"))
