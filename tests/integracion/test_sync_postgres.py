"""Sincronizacion SQLite -> PostgreSQL REAL (schema `pos`), de punta a punta.

Aplica las migraciones 002 y 004 a una base PostgreSQL de pruebas y publica lo que
generan los casos de uso reales (SQLite + cola) mediante el AdaptadorSupabase real.

Requiere un PostgreSQL de pruebas (se OMITE si no hay):

    docker run -d --name pos-pg-test -e POSTGRES_PASSWORD=postgres -p 55432:5432 postgres:16
    POS_TEST_PG_URL=postgresql://postgres:postgres@localhost:55432/postgres pytest

ADVERTENCIA: el test borra y recrea el schema `pos` de la base indicada. Nunca apuntarlo
a Supabase de produccion.
"""

import os
from decimal import Decimal
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja  # noqa: E402
from pos.aplicacion.casos_uso.cerrar_turno_caja import CerrarTurnoCaja  # noqa: E402
from pos.aplicacion.casos_uso.registrar_movimiento_caja import RegistrarMovimientoCaja  # noqa: E402
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto  # noqa: E402
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta  # noqa: E402
from pos.aplicacion.casos_uso.sincronizar_pendientes import SincronizarPendientes  # noqa: E402
from pos.aplicacion.sincronizacion import encolar_existencia, encolar_venta  # noqa: E402
from pos.dominio.caja import TipoMovimientoCaja  # noqa: E402
from pos.dominio.inventario import Existencia  # noqa: E402
from pos.dominio.pagos import MedioPago, Pago  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_existencias import (  # noqa: E402
    RepositorioExistenciasSQLite,
)
from pos.infraestructura.sqlite.repositorio_productos import (  # noqa: E402
    RepositorioProductosSQLite,
)
from pos.infraestructura.sqlite.repositorio_turnos_caja import (  # noqa: E402
    RepositorioTurnosCajaSQLite,
)
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite  # noqa: E402
from pos.infraestructura.supabase.adaptador_supabase import AdaptadorSupabase  # noqa: E402

PG_URL = os.environ.get("POS_TEST_PG_URL")
MIGRACIONES = Path(__file__).resolve().parents[2] / "database" / "migraciones"

pytestmark = pytest.mark.skipif(
    not PG_URL, reason="define POS_TEST_PG_URL para probar contra PostgreSQL"
)


@pytest.fixture
def pg():
    """Conexion a un schema `pos` recien migrado (002 + quitar check de 003 + 004)."""
    con = psycopg2.connect(PG_URL)
    con.autocommit = True
    cur = con.cursor()
    cur.execute("DROP SCHEMA IF EXISTS pos CASCADE; CREATE SCHEMA pos; SET search_path TO pos;")
    cur.execute((MIGRACIONES / "002_modelo_completo.sql").read_text())
    cur.execute("ALTER TABLE producto DROP CONSTRAINT IF EXISTS producto_no_vende_bajo_costo;")
    cur.execute((MIGRACIONES / "004_sincronizacion.sql").read_text())
    cur.execute("RESET search_path;")
    yield cur
    cur.execute("DROP SCHEMA IF EXISTS pos CASCADE;")
    con.close()


class App:
    """Casos de uso reales sobre SQLite en memoria, con la cola de sincronizacion conectada."""

    def __init__(self):
        con = crear_conexion(":memory:")
        crear_esquema(con)
        self.cola = ColaSincronizacionSQLite(con)
        self.productos = RepositorioProductosSQLite(con)
        self.existencias = RepositorioExistenciasSQLite(con)
        self.turnos = RepositorioTurnosCajaSQLite(con)
        self.ventas = RepositorioVentasSQLite(con)
        self.registrar_producto = RegistrarProducto(self.productos, cola=self.cola)
        self.abrir = AbrirTurnoCaja(self.turnos, cola=self.cola)
        self.cerrar = CerrarTurnoCaja(self.turnos, self.ventas, cola=self.cola)
        self.movimiento = RegistrarMovimientoCaja(self.turnos, cola=self.cola)
        self.venta = RegistrarVenta(
            self.ventas, self.turnos, self.productos, self.existencias, cola=self.cola
        )

    def sembrar(self, codigo, nombre, precio, stock, **kw):
        self.registrar_producto.ejecutar(codigo, nombre, precio, **kw)
        existencia = Existencia(codigo, Decimal(str(stock)))
        self.existencias.guardar(existencia)
        encolar_existencia(self.cola, existencia)

    def vender(self, items, pagos):
        venta = self.venta.iniciar(usuario_id=1)
        for codigo, cantidad in items:
            self.venta.agregar_producto(venta, codigo, cantidad)
        for pago in pagos:
            self.venta.agregar_pago(venta, pago)
        return self.venta.cerrar(venta)

    def sincronizar(self):
        return SincronizarPendientes(
            self.cola, AdaptadorSupabase(PG_URL, sslmode="disable")
        ).ejecutar()


def _uno(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def _jornada_completa(app):
    app.sembrar("20001", "VGAN Brownie", 1990, 25)
    app.sembrar("20002", "Fatbombs Nutella", 2490, 15)
    app.abrir.ejecutar(usuario_id=1, fondo_inicial=Dinero(15_000))
    app.vender(
        [("20001", 2), ("20002", 1)],
        [Pago(medio=MedioPago.TARJETA, monto=Dinero(6470))],
    )
    app.movimiento.ejecutar(TipoMovimientoCaja.RETIRO, Dinero(3000), "retiro por resguardo")
    app.cerrar.ejecutar(efectivo_contado=Dinero(12_000))


def test_jornada_completa_llega_a_postgres_sin_perdida(pg):
    app = App()
    _jornada_completa(app)

    resultado = app.sincronizar()

    assert resultado.fallo_en is None
    assert app.cola.pendientes() == []
    assert _uno(pg, "SELECT count(*) FROM pos.producto") == 2
    assert _uno(
        pg,
        "SELECT cantidad FROM pos.existencia e JOIN pos.producto p "
        "ON p.id=e.producto_id WHERE p.codigo='20001'",
    ) == Decimal("23.000")
    assert _uno(pg, "SELECT count(*) FROM pos.turno_caja WHERE cerrado_en IS NOT NULL") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.movimiento_caja") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.venta") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.venta_detalle") == 2
    assert _uno(pg, "SELECT sum(monto) FROM pos.venta_pago") == Decimal("6470.00")
    # El stock remoto refleja la venta (25-2 y 15-1) y el total vendido calza con SQLite.
    assert _uno(pg, "SELECT sum(cantidad*precio_unitario) FROM pos.venta_detalle") == Decimal(
        "6470.00"
    )


def test_publicar_dos_veces_no_duplica(pg):
    app = App()
    _jornada_completa(app)
    operaciones = app.cola.pendientes()
    adaptador = AdaptadorSupabase(PG_URL, sslmode="disable")

    for _ in range(2):  # reintento completo, como tras un corte de red
        for op in operaciones:
            adaptador.publicar(op)

    assert _uno(pg, "SELECT count(*) FROM pos.venta") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.venta_detalle") == 2
    assert _uno(pg, "SELECT count(*) FROM pos.venta_pago") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.movimiento_caja") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.turno_caja") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.producto") == 2


def test_corte_a_mitad_se_retoma_sin_perder_ni_duplicar(pg):
    app = App()
    _jornada_completa(app)
    total = len(app.cola.pendientes())
    real = AdaptadorSupabase(PG_URL, sslmode="disable")

    class CaeEnLaSexta:
        def __init__(self):
            self.vistas = 0

        def publicar(self, op):
            self.vistas += 1
            if self.vistas == 6:
                raise ConnectionError("se cayo internet")
            real.publicar(op)

    primero = SincronizarPendientes(app.cola, CaeEnLaSexta()).ejecutar()
    assert primero.sincronizadas == 5 and primero.fallo_en is not None
    assert len(app.cola.pendientes()) == total - 5

    segundo = app.sincronizar()  # vuelve internet
    assert segundo.fallo_en is None and app.cola.pendientes() == []
    assert _uno(pg, "SELECT count(*) FROM pos.venta") == 1
    assert _uno(pg, "SELECT count(*) FROM pos.venta_detalle") == 2
    assert _uno(pg, "SELECT count(*) FROM pos.movimiento_caja") == 1


def test_venta_sin_su_turno_remoto_queda_pendiente_y_no_se_pierde(pg):
    """Si la venta llega antes que su turno, NO se marca como sincronizada en falso."""
    app = App()
    app.sembrar("20001", "VGAN Brownie", 1990, 25)
    app.abrir.ejecutar(usuario_id=1, fondo_inicial=Dinero(15_000))
    app.vender([("20001", 1)], [Pago(medio=MedioPago.TARJETA, monto=Dinero(1990))])
    pendientes = app.cola.pendientes()
    venta_op = next(op for op in pendientes if op["entidad"] == "venta")
    adaptador = AdaptadorSupabase(PG_URL, sslmode="disable")
    for op in pendientes:  # productos y existencias, pero NO el turno
        if op["entidad"] in {"producto", "existencia"}:
            adaptador.publicar(op)

    with pytest.raises(RuntimeError):
        adaptador.publicar(venta_op)

    assert _uno(pg, "SELECT count(*) FROM pos.venta") == 0  # la transaccion se revirtio
    # Con el orden correcto de la cola, el mismo reintento si funciona.
    assert app.sincronizar().fallo_en is None
    assert _uno(pg, "SELECT count(*) FROM pos.venta") == 1


def test_catalogo_inicial_se_puede_encolar_y_publicar(pg):
    app = App()
    app.productos.guardar(
        __import__("pos.dominio.productos", fromlist=["Producto"]).Producto(
            "777", "Granola", Dinero(3500)
        )
    )
    app.existencias.guardar(Existencia("777", Decimal("4")))
    from pos.aplicacion.sincronizacion import encolar_catalogo

    n = encolar_catalogo(app.cola, app.productos.listar(), [app.existencias.obtener("777")])
    assert n == 2
    assert app.sincronizar().fallo_en is None
    assert _uno(pg, "SELECT precio_venta FROM pos.producto WHERE codigo='777'") == Decimal(
        "3500.00"
    )


def test_encolar_venta_helper_es_idempotente_en_la_cola():
    app = App()
    app.sembrar("20001", "VGAN Brownie", 1990, 25)
    app.abrir.ejecutar(usuario_id=1, fondo_inicial=Dinero(0))
    venta = app.vender([("20001", 1)], [Pago(medio=MedioPago.TARJETA, monto=Dinero(1990))])
    antes = len(app.cola.pendientes())
    encolar_venta(app.cola, venta, app.turnos.obtener_abierto().uuid)  # doble encolado
    assert len(app.cola.pendientes()) == antes
