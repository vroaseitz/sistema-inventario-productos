"""Regresiones de la revision de codigo independiente del 19-11 (cada hallazgo, con su prueba)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.anular_venta import AnularVenta
from pos.aplicacion.casos_uso.gestionar_clientes import GestionarClientes, PagarEstadoDeCuenta
from pos.aplicacion.casos_uso.migrar_datos_legados import (
    COLUMNAS_CLIENTES,
    COLUMNAS_PRODUCTOS,
    MigrarClientes,
    MigrarProductos,
)
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.aplicacion.casos_uso.sincronizar_pendientes import SincronizarPendientes
from pos.aplicacion.puertos import OperacionIncompleta, OperacionRechazada
from pos.dominio.clientes import (
    DETALLE_SALDO_ANTERIOR,
    MEDIO_SALDO_A_FAVOR,
    MovimientoCliente,
    TipoMovimientoCliente,
    consumos_del_ciclo,
    creditos_del_ciclo,
    falta_pagar,
    saldo_de,
)
from pos.dominio.errores import ReglaVentaInvalida
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.dominio.ventas import DestinoDevolucion, EstadoVenta
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
from pos.infraestructura.sqlite.repositorio_categorias import RepositorioCategoriasSQLite
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite

HOY = date.today()


@pytest.fixture
def con(tmp_path):
    c = crear_conexion(str(tmp_path / "r.db"))
    crear_esquema(c)
    return c


# --- 1) saldo a favor + pagar el estado de cuenta ----------------------------------------------


def test_un_cliente_con_saldo_a_favor_puede_pagar_su_estado_de_cuenta(con):
    clientes = RepositorioClientesSQLite(con)
    cliente = GestionarClientes(clientes).crear("Ana", "+56 9 1", cupo=50000)
    for tipo, monto, medio, detalle in (
        (TipoMovimientoCliente.CONSUMO, 10000, None, "Venta"),
        (TipoMovimientoCliente.ABONO, 10000, MEDIO_SALDO_A_FAVOR, "Saldo a favor"),
    ):
        clientes.agregar_movimiento(
            MovimientoCliente(cliente.id, tipo, monto, HOY, detalle, medio=medio)
        )
    movs = clientes.movimientos(cliente.id)
    assert saldo_de(movs) == 0
    # «Falta pagar» ya descuenta lo que el cliente tenia a favor: 10.000 - 20 % - 10.000
    assert falta_pagar(10000, creditos_del_ciclo(movs, HOY.year, HOY.month)) == -2000

    pagador = PagarEstadoDeCuenta(clientes)
    assert pagador.calcular(cliente.id, HOY.year, HOY.month) == (0, 2000)  # sin error
    pagador.ejecutar(cliente.id, HOY.year, HOY.month)
    assert saldo_de(clientes.movimientos(cliente.id)) == -2000  # «A favor $2.000»


# --- 2) importador: decimales ambiguos y nombres repetidos ------------------------------------


def _fila_p(**kw):
    base = {
        "codigo": "X1", "nombre": "Algo", "unidad_venta": "unidad", "categoria": "Líquidos",
        "precio_venta_con_iva": "1000", "costo_neto": "", "iva": "", "impuesto_adicional": "",
        "existencia": "1", "stock_minimo": "",
    }  # fmt: skip
    return {**base, **kw}


@pytest.mark.parametrize("malo", ["1500.50", "12,5", "1500,0", "abc", "-5"])
def test_el_importador_rechaza_decimales_en_vez_de_multiplicarlos(con, malo):
    assert set(COLUMNAS_PRODUCTOS) <= set(_fila_p())
    resumen = MigrarProductos(
        RepositorioProductosSQLite(con),
        RepositorioCategoriasSQLite(con),
        RepositorioExistenciasSQLite(con),
    ).ejecutar([_fila_p(precio_venta_con_iva=malo)])
    assert resumen.cargados == 0 and "precio" in resumen.rechazados[0].motivo


def test_el_importador_acepta_enteros_con_o_sin_separador_de_miles(con):
    repo = RepositorioProductosSQLite(con)
    MigrarProductos(
        repo, RepositorioCategoriasSQLite(con), RepositorioExistenciasSQLite(con)
    ).ejecutar(
        [
            _fila_p(codigo="A", precio_venta_con_iva="12990"),
            _fila_p(codigo="B", precio_venta_con_iva="12.990"),
        ]
    )
    assert repo.obtener_por_codigo("A").precio.monto == repo.obtener_por_codigo("B").precio.monto


def test_dos_clientes_con_el_mismo_nombre_en_el_archivo_no_se_pierden_en_silencio(con):
    assert "nombre" in COLUMNAS_CLIENTES
    fila = {"nombre": "Pedro Gómez", "telefono": "1", "observaciones": "", "cupo": "1000",
            "deuda_actual": "5000", "ultimo_pago": ""}  # fmt: skip
    resumen = MigrarClientes(RepositorioClientesSQLite(con), lambda: HOY).ejecutar(
        [fila, {**fila, "deuda_actual": "9000"}]
    )
    assert resumen.cargados == 1 and resumen.omitidos == 0
    assert "repetido" in resumen.rechazados[0].motivo  # el segundo se ve, no desaparece


# --- 3) la deuda heredada no recibe el 20 % --------------------------------------------------


def test_el_saldo_anterior_de_la_migracion_no_cuenta_como_consumo_del_ciclo(con):
    clientes = RepositorioClientesSQLite(con)
    cliente = GestionarClientes(clientes).crear("Luis", "+56 9 2")
    mes_anterior = date(HOY.year, HOY.month, 1).replace(day=1)
    clientes.agregar_movimiento(
        MovimientoCliente(
            cliente.id, TipoMovimientoCliente.CONSUMO, 12000, mes_anterior, DETALLE_SALDO_ANTERIOR
        )
    )
    movs = clientes.movimientos(cliente.id)
    assert saldo_de(movs) == 12000  # la deuda existe
    assert consumos_del_ciclo(movs, mes_anterior.year, mes_anterior.month) == 0  # sin descuento


# --- 4) anular: validar antes de tocar nada; constancia del reembolso por terminal ------------


def _mundo(con, con_caja=False):
    productos = RepositorioProductosSQLite(con)
    existencias = RepositorioExistenciasSQLite(con)
    turnos = RepositorioTurnosCajaSQLite(con)
    ventas = RepositorioVentasSQLite(con)
    productos.guardar(Producto("ARR", "Arroz", Dinero(1000), categoria_id=1))
    existencias.guardar(Existencia("ARR", Decimal("20")))
    AbrirTurnoCaja(turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    registrar = RegistrarVenta(ventas, turnos, productos, existencias)
    auditoria = RepositorioAuditoriaSQLite(con)
    anular = AnularVenta(ventas, turnos, existencias, auditor=Auditor(auditoria, lambda: "Admin"))
    return registrar, anular, ventas, existencias, auditoria


def _vender(registrar, medio, cantidad=2):
    v = registrar.iniciar(usuario_id=1)
    registrar.agregar_producto(v, "ARR", cantidad)
    registrar.agregar_pago(v, Pago(medio, Dinero(v.total.monto)))
    return registrar.cerrar(v)


def test_si_falta_la_caja_no_se_toca_ni_el_stock_ni_la_venta(con):
    registrar, anular, ventas, existencias, _ = _mundo(con)  # sin registrar_movimiento_caja
    v = _vender(registrar, MedioPago.EFECTIVO)
    stock = existencias.obtener("ARR").cantidad
    with pytest.raises(ReglaVentaInvalida, match="salida de caja"):
        anular.ejecutar(v.id, "Producto en mal estado", "", "Admin", DestinoDevolucion.EFECTIVO)
    assert existencias.obtener("ARR").cantidad == stock  # no se repuso a medias
    assert ventas.obtener(v.id).estado is EstadoVenta.PAGADA


def test_un_pago_con_tarjeta_deja_constancia_del_reembolso_pendiente(con):
    registrar, anular, _, _, auditoria = _mundo(con)
    v = _vender(registrar, MedioPago.TARJETA)  # sin cliente: no hay opciones de dinero
    anular.ejecutar(v.id, "Producto en mal estado", "", "Admin")
    filas = auditoria.listar(accion="Reembolso pendiente por tarjeta o transferencia")
    assert len(filas) == 1 and "$2.000" in filas[0]["antes"]


# --- 5) la sincronizacion arrastra el rechazo de una venta a su anulacion ----------------------


def test_una_venta_rechazada_arrastra_a_su_anulacion_sin_frenar_la_cola(tmp_path):
    c = crear_conexion(str(tmp_path / "s.db"))
    crear_esquema(c)
    cola = ColaSincronizacionSQLite(c)
    cola.encolar("venta", "insert", {"uuid": "V1", "detalles": []}, "op-1")
    cola.encolar("venta_anular", "update", {"uuid": "V1", "motivo": "x"}, "op-2")
    cola.encolar("producto", "upsert", {"codigo": "OK"}, "op-3")

    class Pub:
        publicadas: list[str] = []  # noqa: RUF012

        def publicar(self, op):
            if op["entidad"] == "venta":
                raise OperacionRechazada("restriccion")
            if op["entidad"] == "venta_anular":
                raise OperacionIncompleta("la venta no llego")
            self.publicadas.append(op["id_cliente"])

    pub = Pub()
    resultado = SincronizarPendientes(cola, pub).ejecutar()
    assert resultado.fallo_en is None and resultado.rechazadas == 2
    assert pub.publicadas == ["op-3"]  # lo demas siguio llegando
    assert {r["id_cliente"] for r in cola.rechazadas()} == {"op-1", "op-2"}
