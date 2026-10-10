"""Pruebas end-to-end del flujo de venta y caja contra SQLite real (base en memoria).

Ejercitan los casos de uso completos (no dobles en memoria): abrir turno, registrar
ventas con distintos medios de pago, movimientos de caja y cierre con arqueo,
pasando siempre por los repositorios SQLite reales. Cubren HU-VTA-01, HU-VTA-03,
HU-VTA-04, HU-CAJ-01, HU-CAJ-02, HU-CAJ-03 y HU-CAJ-04.
"""

from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.dominio.caja import TipoMovimientoCaja
from pos.dominio.errores import ReglaCajaInvalida, ReglaVentaInvalida
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago, calcular_cobro_efectivo
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Costo, Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite


@pytest.fixture
def conexion():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    yield con
    con.close()


@pytest.fixture
def repos(conexion):
    repo_productos = RepositorioProductosSQLite(conexion)
    repo_existencias = RepositorioExistenciasSQLite(conexion)
    repo_turnos = RepositorioTurnosCajaSQLite(conexion)
    repo_ventas = RepositorioVentasSQLite(conexion)
    return repo_productos, repo_existencias, repo_turnos, repo_ventas


def _sembrar_producto(repo_productos, repo_existencias, codigo, precio, costo_neto, stock):
    costo = Costo(Dinero(costo_neto), Dinero(0))
    repo_productos.guardar(Producto(codigo, f"Producto {codigo}", Dinero(precio), costo=costo))
    repo_existencias.guardar(Existencia(codigo, Decimal(str(stock))))


def test_flujo_completo_apertura_venta_y_cierre(repos):
    repo_productos, repo_existencias, repo_turnos, repo_ventas = repos
    _sembrar_producto(
        repo_productos, repo_existencias, "12345", precio=1235, costo_neto=800, stock=10
    )

    turno = AbrirTurnoCaja(repo_turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(15_000))
    assert turno.id is not None

    registrar = RegistrarVenta(repo_ventas, repo_turnos, repo_productos, repo_existencias)
    venta = registrar.iniciar(usuario_id=1)
    registrar.agregar_producto(venta, "12345", 1)
    cobro = calcular_cobro_efectivo(venta.total, monto_entregado=Dinero(2000))
    registrar.agregar_pago(
        venta, Pago(medio=MedioPago.EFECTIVO, monto=cobro.total_redondeado, cobro_efectivo=cobro)
    )
    registrar.cerrar(venta)

    assert venta.id is not None
    # El stock se descuenta de verdad en SQLite, no solo en memoria.
    assert repo_existencias.obtener("12345").cantidad == Decimal("9")

    # El cajon queda con el fondo inicial mas la venta neta: lo entregado por el
    # cliente ($2.000) menos el vuelto que salio ($770) = $1.230, igual al total
    # ya redondeado.
    arqueo = CerrarTurnoCaja(repo_turnos, repo_ventas).ejecutar(
        efectivo_contado=Dinero(15_000 + 1230)
    )
    assert arqueo.totales_por_medio[MedioPago.EFECTIVO] == Dinero(1230)
    assert arqueo.diferencia == 0
    assert repo_turnos.obtener_abierto() is None


def test_no_se_puede_abrir_dos_turnos_a_la_vez(repos):
    _, _, repo_turnos, _ = repos
    AbrirTurnoCaja(repo_turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(15_000))
    with pytest.raises(ReglaCajaInvalida):
        AbrirTurnoCaja(repo_turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(15_000))


def test_no_se_puede_vender_sin_turno_abierto(repos):
    repo_productos, repo_existencias, repo_turnos, repo_ventas = repos
    registrar = RegistrarVenta(repo_ventas, repo_turnos, repo_productos, repo_existencias)
    with pytest.raises(ReglaCajaInvalida):
        registrar.iniciar(usuario_id=1)


def test_venta_con_stock_insuficiente_no_persiste_nada(repos):
    # Si el cierre falla, la venta no debe quedar guardada ni el stock descontado:
    # ni en memoria ni en la tabla ventas.
    repo_productos, repo_existencias, repo_turnos, repo_ventas = repos
    _sembrar_producto(
        repo_productos, repo_existencias, "12345", precio=1000, costo_neto=500, stock=1
    )

    AbrirTurnoCaja(repo_turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    registrar = RegistrarVenta(repo_ventas, repo_turnos, repo_productos, repo_existencias)
    venta = registrar.iniciar(usuario_id=1)
    registrar.agregar_producto(venta, "12345", 5)  # pide 5, solo hay 1
    venta.agregar_pago(Pago(medio=MedioPago.TARJETA, monto=Dinero(5000)))

    with pytest.raises(ReglaVentaInvalida):
        registrar.cerrar(venta)

    assert venta.id is None
    assert repo_existencias.obtener("12345").cantidad == Decimal("1")
    turno = repo_turnos.obtener_abierto()
    assert repo_ventas.obtener_por_turno(turno.id) == []


def test_pago_combinado_tarjeta_y_efectivo_persiste_ambos_pagos(repos):
    repo_productos, repo_existencias, repo_turnos, repo_ventas = repos
    _sembrar_producto(
        repo_productos, repo_existencias, "12345", precio=2235, costo_neto=1000, stock=5
    )

    AbrirTurnoCaja(repo_turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    registrar = RegistrarVenta(repo_ventas, repo_turnos, repo_productos, repo_existencias)
    venta = registrar.iniciar(usuario_id=1)
    registrar.agregar_producto(venta, "12345", 1)
    registrar.agregar_pago(venta, Pago(medio=MedioPago.TARJETA, monto=Dinero(2000)))
    resto = Dinero(venta.total.monto - 2000)
    cobro = calcular_cobro_efectivo(resto, monto_entregado=Dinero(300))
    registrar.agregar_pago(
        venta, Pago(medio=MedioPago.EFECTIVO, monto=cobro.total_redondeado, cobro_efectivo=cobro)
    )
    registrar.cerrar(venta)

    turno = repo_turnos.obtener_abierto()
    (recargada,) = repo_ventas.obtener_por_turno(turno.id)
    assert len(recargada.pagos) == 2
    medios = {p.medio for p in recargada.pagos}
    assert medios == {MedioPago.TARJETA, MedioPago.EFECTIVO}
    assert recargada.total_pagado == Dinero(2230)


def test_leer_dos_veces_el_mismo_producto_no_duplica_la_linea(repos):
    repo_productos, repo_existencias, repo_turnos, repo_ventas = repos
    _sembrar_producto(
        repo_productos, repo_existencias, "12345", precio=1000, costo_neto=500, stock=10
    )

    AbrirTurnoCaja(repo_turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    registrar = RegistrarVenta(repo_ventas, repo_turnos, repo_productos, repo_existencias)
    venta = registrar.iniciar(usuario_id=1)
    registrar.agregar_producto(venta, "12345", 1)
    registrar.agregar_producto(venta, "12345", 1)
    assert len(venta.detalles) == 1
    assert venta.detalles[0].cantidad == Decimal("2")

    registrar.agregar_pago(venta, Pago(medio=MedioPago.TARJETA, monto=Dinero(2000)))
    registrar.cerrar(venta)

    turno = repo_turnos.obtener_abierto()
    (recargada,) = repo_ventas.obtener_por_turno(turno.id)
    assert len(recargada.detalles) == 1
    assert recargada.detalles[0].cantidad == Decimal("2")
    assert repo_existencias.obtener("12345").cantidad == Decimal("8")


def test_movimientos_de_caja_afectan_el_arqueo_final(repos):
    # HU-CAJ-04 + HU-CAJ-02 de punta a punta: retiro e ingreso reales en SQLite,
    # reflejados en el arqueo de cierre.
    _, _, repo_turnos, repo_ventas = repos
    AbrirTurnoCaja(repo_turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(15_000))

    mover = RegistrarMovimientoCaja(repo_turnos)
    mover.ejecutar(TipoMovimientoCaja.RETIRO, Dinero(3000), motivo="pago a proveedor")
    mover.ejecutar(TipoMovimientoCaja.INGRESO, Dinero(1000), motivo="cambio chico")

    arqueo = CerrarTurnoCaja(repo_turnos, repo_ventas).ejecutar(
        efectivo_contado=Dinero(15_000 - 3000 + 1000)
    )
    assert arqueo.diferencia == 0
    assert arqueo.retiros_caja == Dinero(3000)
    assert arqueo.ingresos_caja == Dinero(1000)


def test_movimiento_de_caja_sin_turno_abierto_falla(repos):
    _, _, repo_turnos, _ = repos
    with pytest.raises(ReglaCajaInvalida):
        RegistrarMovimientoCaja(repo_turnos).ejecutar(
            TipoMovimientoCaja.RETIRO, Dinero(1000), motivo="x"
        )


def test_cerrar_sin_turno_abierto_falla(repos):
    _, _, repo_turnos, repo_ventas = repos
    with pytest.raises(ReglaCajaInvalida):
        CerrarTurnoCaja(repo_turnos, repo_ventas).ejecutar(efectivo_contado=Dinero(0))
