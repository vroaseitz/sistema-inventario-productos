"""Migración de productos y clientes del sistema antiguo (QA 18-11), con CSV de ejemplo."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from pos.aplicacion.casos_uso.migrar_datos_legados import (
    COLUMNAS_CLIENTES,
    COLUMNAS_PRODUCTOS,
    ErrorArchivo,
    MigrarClientes,
    MigrarProductos,
    leer_csv,
)
from pos.aplicacion.registro_movimientos import RegistroMovimientos
from pos.dominio.clientes import saldo_de
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_categorias import RepositorioCategoriasSQLite
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite
from pos.infraestructura.sqlite.repositorio_existencias import RepositorioExistenciasSQLite
from pos.infraestructura.sqlite.repositorio_movimientos import RepositorioMovimientosSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import importar_migracion  # noqa: E402

CABECERA_P = (
    "codigo;nombre;unidad_venta;categoria;origen_categoria;precio_venta_con_iva;costo_neto;iva;"
    "impuesto_adicional;costo_total_antiguo;existencia;stock_minimo;ultima_venta;en_los_1135;"
    "origen;observaciones"
)
FILAS_P = [
    "A1;GRANOLA EJEMPLO;unidad;Granolas y cereales;x;3990;2000;380;0;2380;12;;2026-11-01;si;ficha;",
    "A2;ALMENDRA EJEMPLO;granel;Frutos secos y semillas;x;14990;8000;1520;0;9520;2,350;3;;si;"
    "ficha;",
    "A3;BEBIDA EJEMPLO;unidad;Líquidos;x;1500;700;133;70;903;0;;;si;ficha;",
    "A4;SIN FICHA EJEMPLO;unidad;Sin categoría;x;990;;;;;5;;;no;sin ficha;",
    "5550001;;unidad;Líquidos;x;1000;500;95;0;595;1;;;si;ficha;",  # sin nombre, código numérico
]
CABECERA_C = "nombre;telefono;observaciones;cupo;deuda_actual;ultimo_pago"
FILAS_C = [
    "Cliente Uno;+56 9 1111 1111;vive cerca;50000;12000;2026-10-02",
    "Cliente Dos;;;100000;0;",
    ";;;5000;0;",  # sin nombre
]


def _csv(ruta: Path, cabecera: str, filas: list[str]) -> Path:
    ruta.write_bytes(("﻿" + "\r\n".join([cabecera, *filas]) + "\r\n").encode("utf-8"))
    return ruta


@pytest.fixture
def con(tmp_path):
    c = crear_conexion(str(tmp_path / "t.db"))
    crear_esquema(c)
    return c


def _productos(con, cola=None):
    return MigrarProductos(
        RepositorioProductosSQLite(con),
        RepositorioCategoriasSQLite(con),
        RepositorioExistenciasSQLite(con),
        RegistroMovimientos(RepositorioMovimientosSQLite(con), lambda: "migración"),
        cola,
    )


def _filas_p(tmp_path):
    return leer_csv(_csv(tmp_path / "p.csv", CABECERA_P, FILAS_P), COLUMNAS_PRODUCTOS)


def test_productos_con_categoria_costo_y_carga_inicial(con, tmp_path):
    resumen = _productos(con).ejecutar(_filas_p(tmp_path))

    assert (resumen.leidos, resumen.cargados, resumen.omitidos) == (5, 4, 0)
    assert [r.fila for r in resumen.rechazados] == [6]
    repo = RepositorioProductosSQLite(con)
    bebida = repo.obtener_por_codigo("A3")
    # El costo neto de las bebidas ya incluye el IABA (PO, CA-21): no se separa al migrar.
    assert bebida.costo.neto.monto == 700
    assert any("IABA" in a for a in resumen.avisos)
    assert repo.obtener_por_codigo("A4").costo is None
    assert repo.obtener_por_codigo("A2").stock_minimo == 3
    cat = RepositorioCategoriasSQLite(con).nombre_de(repo.obtener_por_codigo("A4").categoria_id)
    assert cat == "Sin categoría"
    existencias = RepositorioExistenciasSQLite(con)
    assert existencias.obtener("A2").cantidad == Decimal("2.350")
    assert existencias.obtener("A3").cantidad == 0
    cargas = RepositorioMovimientosSQLite(con).listar(codigo="A1")
    assert [(m.cantidad, m.motivo) for m in cargas] == [(Decimal(12), "Carga inicial")]
    assert RepositorioMovimientosSQLite(con).listar(codigo="A3") == []  # stock 0: sin movimiento


def test_sin_nombre_pero_con_codigo_de_texto_usa_el_codigo(con, tmp_path):
    fila = "FUDGE;;unidad;Sin categoría;x;1000;;;;;2;;;si;ficha;"
    filas = leer_csv(_csv(tmp_path / "n.csv", CABECERA_P, [fila]), COLUMNAS_PRODUCTOS)
    resumen = _productos(con).ejecutar(filas)
    assert resumen.cargados == 1
    assert RepositorioProductosSQLite(con).obtener_por_codigo("FUDGE").nombre == "FUDGE"
    assert any("código como nombre" in a for a in resumen.avisos)


def test_productos_es_idempotente(con, tmp_path):
    filas = _filas_p(tmp_path)
    _productos(con).ejecutar(filas)
    existencias = RepositorioExistenciasSQLite(con)
    existencias.guardar(type(existencias.obtener("A1"))("A1", Decimal(3)))  # se vendio stock

    segunda = _productos(con).ejecutar(filas)

    assert (segunda.cargados, segunda.omitidos) == (0, 4)
    assert existencias.obtener("A1").cantidad == 3  # no se pisa el stock vivo
    assert len(RepositorioMovimientosSQLite(con).listar(codigo="A1")) == 1


def test_productos_se_encolan_para_supabase(con, tmp_path):
    cola = ColaSincronizacionSQLite(con)
    _productos(con, cola).ejecutar(_filas_p(tmp_path))
    entidades = [p["entidad"] for p in cola.pendientes()]
    assert entidades.count("producto") == 4
    assert entidades.count("existencia") == 4


def test_producto_con_unidad_o_numero_malo_se_rechaza_con_motivo(con, tmp_path):
    malas = [
        "B1;X;caja;Líquidos;x;100;;;;;1;;;si;ficha;",
        "B2;X;unidad;Líquidos;x;abc;;;;;1;;;si;ficha;",
    ]
    filas = leer_csv(_csv(tmp_path / "m.csv", CABECERA_P, malas), COLUMNAS_PRODUCTOS)
    resumen = _productos(con).ejecutar(filas)
    assert resumen.cargados == 0
    assert "unidad de venta" in resumen.rechazados[0].motivo
    assert "precio" in resumen.rechazados[1].motivo


def _clientes(con, cola=None, fecha=date(2026, 10, 31)):
    return MigrarClientes(RepositorioClientesSQLite(con), lambda: fecha, cola)


def _filas_c(tmp_path):
    return leer_csv(_csv(tmp_path / "c.csv", CABECERA_C, FILAS_C), COLUMNAS_CLIENTES)


def test_clientes_con_cupo_y_saldo_anterior(con, tmp_path):
    resumen = _clientes(con).ejecutar(_filas_c(tmp_path))

    assert (resumen.cargados, resumen.omitidos, len(resumen.rechazados)) == (2, 0, 1)
    assert "falta el nombre" in resumen.rechazados[0].motivo
    assert "nombre" not in resumen.rechazados[0].referencia.lower()
    repo = RepositorioClientesSQLite(con)
    uno, dos = repo.listar()
    assert uno.cupo == 50000 and uno.observaciones == "vive cerca"
    movs = repo.movimientos(uno.id)
    assert saldo_de(movs) == 12000
    assert movs[0].fecha == date(2026, 10, 31)
    assert movs[0].detalle.startswith("Saldo anterior") and "2026-10-02" in movs[0].detalle
    assert repo.movimientos(dos.id) == []  # deuda 0: sin movimiento
    assert any("sin teléfono" in a.lower() or "no traían teléfono" in a for a in resumen.avisos)


def test_clientes_es_idempotente_y_no_duplica_el_saldo(con, tmp_path):
    filas = _filas_c(tmp_path)
    _clientes(con).ejecutar(filas)
    segunda = _clientes(con).ejecutar(filas)

    assert (segunda.cargados, segunda.omitidos) == (0, 2)
    repo = RepositorioClientesSQLite(con)
    assert saldo_de(repo.movimientos(repo.listar()[0].id)) == 12000


def test_columnas_faltantes_se_avisan(tmp_path):
    ruta = _csv(tmp_path / "x.csv", "codigo;nombre", ["1;a"])
    with pytest.raises(ErrorArchivo, match="faltan las columnas"):
        leer_csv(ruta, COLUMNAS_PRODUCTOS)


def test_comando_simulacro_no_guarda_nada(tmp_path, monkeypatch):
    db = tmp_path / "s.db"
    monkeypatch.setenv("POS_SQLITE_PATH", str(db))
    p = _csv(tmp_path / "p.csv", CABECERA_P, FILAS_P)
    c = _csv(tmp_path / "c.csv", CABECERA_C, FILAS_C)

    assert (
        importar_migracion.main(["--productos", str(p), "--clientes", str(c), "--simulacro"]) == 0
    )

    con = crear_conexion(str(db))
    assert RepositorioProductosSQLite(con).listar() == []
    assert RepositorioClientesSQLite(con).listar() == []


def test_comando_guarda_y_deja_el_saldo_en_el_mes_anterior(tmp_path, monkeypatch, capsys):
    db = tmp_path / "g.db"
    monkeypatch.setenv("POS_SQLITE_PATH", str(db))
    p = _csv(tmp_path / "p.csv", CABECERA_P, FILAS_P)
    c = _csv(tmp_path / "c.csv", CABECERA_C, FILAS_C)

    assert importar_migracion.main(["--productos", str(p), "--clientes", str(c)]) == 0

    con = crear_conexion(str(db))
    assert len(RepositorioProductosSQLite(con).listar()) == 4
    cli = RepositorioClientesSQLite(con)
    mov = cli.movimientos(cli.listar()[0].id)[0]
    assert mov.fecha == importar_migracion.fin_de_mes_anterior(date.today())
    assert "4 cargados" in capsys.readouterr().out


def test_fin_de_mes_anterior():
    assert importar_migracion.fin_de_mes_anterior(date(2026, 11, 18)) == date(2026, 10, 31)
    assert importar_migracion.fin_de_mes_anterior(date(2026, 1, 5)) == date(2025, 12, 31)
