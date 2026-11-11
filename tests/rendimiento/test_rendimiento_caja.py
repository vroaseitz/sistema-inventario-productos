"""Rendimiento en caja: con un catalogo grande, buscar y vender deben seguir siendo agiles.

Los umbrales son holgados a proposito (no deben fallar por una maquina lenta, como la VM
Windows 8.1) pero atrapan una regresion de orden de magnitud, p. ej. recorrer todo en memoria.
"""

import time
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite

PRODUCTOS = 5000  # el catalogo real de la tienda ronda esa magnitud


@pytest.fixture(scope="module")
def caja():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    productos = RepositorioProductosSQLite(con)
    existencias = RepositorioExistenciasSQLite(con)
    con.execute("BEGIN")
    for i in range(PRODUCTOS):
        productos.guardar(
            Producto(f"P{i:05d}", f"Producto numero {i}", Dinero(1000), categoria_id=1)
        )
        existencias.guardar(Existencia(f"P{i:05d}", Decimal("1000")))
    con.execute("COMMIT")
    turnos = RepositorioTurnosCajaSQLite(con)
    AbrirTurnoCaja(turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    registrar = RegistrarVenta(RepositorioVentasSQLite(con), turnos, productos, existencias)
    return productos, registrar


def test_buscar_en_un_catalogo_grande_responde_rapido(caja):
    productos, _ = caja
    inicio = time.perf_counter()
    encontrados = productos.buscar("numero 4999")
    assert time.perf_counter() - inicio < 0.5
    assert [p.codigo for p in encontrados] == ["P04999"]


def test_una_venta_de_20_lineas_se_cierra_rapido(caja):
    _, registrar = caja
    inicio = time.perf_counter()
    venta = registrar.iniciar(usuario_id=1)
    for i in range(20):
        registrar.agregar_producto(venta, f"P{i:05d}", 1)
    registrar.agregar_pago(venta, Pago(medio=MedioPago.TARJETA, monto=Dinero(20000)))
    registrar.cerrar(venta)
    assert time.perf_counter() - inicio < 1.0
