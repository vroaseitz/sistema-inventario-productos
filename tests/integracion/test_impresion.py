"""HU-VTA-06: comprobante, reimpresion, corte y cajon (SQLite real, impresora simulada)."""

import subprocess
from decimal import Decimal

import pytest

from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja
from pos.aplicacion.casos_uso.imprimir_comprobante import ImprimirComprobante
from pos.aplicacion.casos_uso.registrar_venta import RegistrarVenta
from pos.dominio.caja import calcular_arqueo
from pos.dominio.comprobante import ANCHO, comprobante_de_venta, corte_de_caja
from pos.dominio.errores import ErrorImpresion
from pos.dominio.inventario import Existencia
from pos.dominio.pagos import MedioPago, Pago
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Dinero
from pos.infraestructura.impresion.escpos import CORTE_PARCIAL, PULSO_CAJON, a_escpos
from pos.infraestructura.impresion.impresoras import (
    ImpresoraEnArchivo,
    ImpresoraSistema,
    crear_impresora,
)
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_configuracion import RepositorioConfiguracionSQLite
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite


class ImpresoraFalsa:
    def __init__(self):
        self.impresos = []
        self.cajones = 0

    def imprimir(self, lineas, abrir_cajon=False):
        self.impresos.append((lineas, abrir_cajon))

    def abrir_cajon(self):
        self.cajones += 1


class ImpresoraRota:
    def imprimir(self, lineas, abrir_cajon=False):
        raise ErrorImpresion("sin papel")

    def abrir_cajon(self):
        raise ErrorImpresion("cajon trabado")


@pytest.fixture
def app(tmp_path):
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        turnos = RepositorioTurnosCajaSQLite(con)
        ventas = RepositorioVentasSQLite(con)
        config = RepositorioConfiguracionSQLite(con)
        impresora = ImpresoraFalsa()

    a = A()
    a.registrar = RegistrarVenta(a.ventas, a.turnos, a.productos, a.existencias)
    a.imprimir = ImprimirComprobante(
        lambda: a.impresora, a.productos, a.ventas, a.config, cajera=lambda: "ana"
    )
    a.productos.guardar(
        Producto("AVE", "Barra de avena con miel y almendras", Dinero(1500), categoria_id=1)
    )
    a.productos.guardar(
        Producto("NUE", "Nueces mariposa", Dinero(18000), UnidadVenta.GRANEL, categoria_id=1)
    )
    for codigo in ("AVE", "NUE"):
        a.existencias.guardar(Existencia(codigo, Decimal("50")))
    AbrirTurnoCaja(a.turnos).ejecutar(usuario_id=1, fondo_inicial=Dinero(10000))
    return a


def _vender(a, medio=MedioPago.EFECTIVO):
    v = a.registrar.iniciar(usuario_id=1)
    a.registrar.agregar_producto(v, "AVE", 1)
    a.registrar.agregar_producto(v, "NUE", Decimal("0.350"))
    if medio is MedioPago.EFECTIVO:
        a.registrar.agregar_pago(v, v.construir_pago_efectivo(monto_entregado=10000))
    else:
        a.registrar.agregar_pago(v, Pago(medio, Dinero(v.total.monto)))
    return a.registrar.cerrar(v)


def test_el_comprobante_cabe_en_el_papel_y_dice_que_no_es_tributario(app):
    venta = _vender(app)
    lineas = comprobante_de_venta(
        venta,
        {"AVE": "Barra de avena con miel y almendras", "NUE": "Nueces mariposa"},
        cajera="ana",
    )
    assert all(len(linea) <= ANCHO for linea in lineas)
    texto = "\n".join(lineas)
    assert "COMPROBANTE DE DETALLE" in texto and "Sin validez tributaria" in texto
    assert "0,350 x $18.000" in texto and "$6.300" in texto  # granel con coma
    assert "TOTAL" in texto and "$7.800" in texto
    assert "Efectivo" in texto and "$10.000" in texto and "Cambio" in texto and "$2.200" in texto
    assert "Atendió: ana" in texto


def test_la_nota_de_la_venta_sale_en_el_comprobante_y_cabe_en_el_papel(app):
    """O-33: la nota (Ctrl+N) no se pierde: aparece en el detalle impreso, en varias lineas."""
    venta = _vender(app)
    venta.nota = "Retira mañana por la tarde; el cliente pide factura a nombre de la empresa"
    lineas = comprobante_de_venta(venta, {"AVE": "Barra de avena", "NUE": "Nueces"})
    assert all(len(linea) <= ANCHO for linea in lineas)
    texto = "\n".join(lineas)
    unido = " ".join(texto.split())  # la nota se parte en lineas de 32 caracteres
    assert (
        "Nota: Retira mañana por la tarde; el cliente pide factura a nombre de la empresa" in unido
    )
    assert texto.index("Nota:") > texto.index("TOTAL")  # va despues del total y los pagos
    venta.nota = "  "
    assert "Nota:" not in "\n".join(comprobante_de_venta(venta, {}))  # sin nota, no hay linea


def test_cobrar_e_imprimir_abre_el_cajon_solo_con_efectivo(app):
    app.imprimir.comprobante(_vender(app))
    app.imprimir.comprobante(_vender(app, MedioPago.TARJETA))
    assert [abrir for _lineas, abrir in app.impresora.impresos] == [True, False]


def test_el_cajon_se_puede_desactivar_en_la_configuracion(app):
    app.config.guardar("abrir_cajon", 0)
    app.imprimir.comprobante(_vender(app))
    app.imprimir.abrir_cajon_si_hubo_efectivo(_vender(app))
    assert app.impresora.impresos[0][1] is False and app.impresora.cajones == 0


def test_cobrar_solo_registrando_igual_abre_el_cajon_si_hubo_efectivo(app):
    app.imprimir.abrir_cajon_si_hubo_efectivo(_vender(app))
    app.imprimir.abrir_cajon_si_hubo_efectivo(_vender(app, MedioPago.TRANSFERENCIA))
    assert app.impresora.impresos == [] and app.impresora.cajones == 1


def test_reimprimir_el_ultimo_no_vuelve_a_abrir_el_cajon(app):
    with pytest.raises(ErrorImpresion, match="Todavia no hay ventas"):
        app.imprimir.reimprimir_ultimo()
    _vender(app)
    ultima = _vender(app)
    reimpresa = app.imprimir.reimprimir_ultimo()
    assert reimpresa.id == ultima.id
    assert app.impresora.impresos[-1][1] is False
    assert f"Venta N° {ultima.id}" in "\n".join(app.impresora.impresos[-1][0])


def test_el_corte_muestra_venta_por_medio_y_efectivo_esperado(app):
    _vender(app)
    turno = app.turnos.obtener_abierto()
    arqueo = calcular_arqueo(turno, app.ventas.obtener_por_turno(turno.id), Dinero(0))
    app.imprimir.corte(turno, arqueo)
    texto = "\n".join(app.impresora.impresos[-1][0])
    assert "CORTE DE CAJA" in texto and "Total vendido" in texto
    assert (
        "Efectivo esperado" in texto and "$17.800" in texto
    )  # fondo 10.000 + 10.000 - cambio 2.200
    assert "Efectivo contado" not in texto  # antes de contar no hay contado
    assert all(len(x) <= ANCHO for x in corte_de_caja(turno, arqueo))


def test_una_impresora_que_falla_avisa_con_ErrorImpresion_y_la_venta_sigue_registrada(app):
    app.impresora = ImpresoraRota()
    venta = _vender(app)
    with pytest.raises(ErrorImpresion, match="sin papel"):
        app.imprimir.comprobante(venta)
    with pytest.raises(ErrorImpresion, match="cajon trabado"):
        app.imprimir.abrir_cajon_si_hubo_efectivo(venta)
    assert app.ventas.ultima().id == venta.id  # nada se deshizo


def test_escpos_codifica_tildes_corta_y_abre_el_cajon():
    datos = a_escpos(["Ñandú café"], abrir_cajon=True)
    assert "Ñandú café".encode("cp858") in datos
    assert datos.endswith(CORTE_PARCIAL + PULSO_CAJON)
    assert PULSO_CAJON not in a_escpos(["x"])


def test_sin_impresora_configurada_los_comprobantes_van_a_archivos(tmp_path):
    impresora = crear_impresora("", tmp_path / "comprobantes")
    assert isinstance(impresora, ImpresoraEnArchivo)
    impresora.imprimir(["hola"], abrir_cajon=True)
    contenido = impresora.ultimo_archivo.read_text(encoding="utf-8")
    assert "hola" in contenido and "cajon" in contenido
    assert isinstance(crear_impresora("Xprinter", tmp_path), ImpresoraSistema)


def test_la_impresora_del_sistema_manda_bytes_crudos_con_lp(monkeypatch):
    llamadas = []
    monkeypatch.setattr("pos.infraestructura.impresion.impresoras.sys.platform", "darwin")
    monkeypatch.setattr(
        subprocess, "run", lambda comando, **k: llamadas.append((comando, k["input"]))
    )
    ImpresoraSistema("Xprinter_58").imprimir(["linea"], abrir_cajon=True)
    comando, datos = llamadas[0]
    assert comando == ["lp", "-d", "Xprinter_58", "-o", "raw"]
    assert datos.endswith(PULSO_CAJON)


def test_si_lp_falla_el_mensaje_nombra_la_impresora(monkeypatch):
    monkeypatch.setattr("pos.infraestructura.impresion.impresoras.sys.platform", "darwin")

    def falla(comando, **k):
        raise subprocess.CalledProcessError(1, comando, stderr=b"impresora desconectada")

    monkeypatch.setattr(subprocess, "run", falla)
    with pytest.raises(ErrorImpresion, match="Xprinter_58.*impresora desconectada"):
        ImpresoraSistema("Xprinter_58").abrir_cajon()
