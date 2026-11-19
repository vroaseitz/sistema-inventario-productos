"""Las lecturas calientes usan indice: sin ellos los reportes son cuadraticos con el historial.

Se revisa el plan de consulta de SQLite (determinista) en vez de medir tiempo, para que no falle
por una maquina lenta como la VM Windows 8.1. Con un ano de ventas, la rentabilidad anual pasaba de
varios minutos a unos segundos al agregar `idx_venta_detalles_venta` y cargar por lotes.
"""

from datetime import date

import pytest

from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_ventas import RepositorioVentasSQLite


@pytest.fixture
def con():
    conexion = crear_conexion(":memory:")
    crear_esquema(conexion)
    return conexion


def _plan(con, sql: str, parametros: tuple = ()) -> str:
    filas = con.execute("EXPLAIN QUERY PLAN " + sql, parametros).fetchall()
    return " | ".join(f["detail"] for f in filas)


def test_detalles_y_pagos_se_buscan_por_indice_de_venta(con):
    assert "idx_venta_detalles_venta" in _plan(
        con, "SELECT * FROM venta_detalles WHERE venta_id = ?", (1,)
    )
    assert "idx_venta_pagos_venta" in _plan(
        con, "SELECT * FROM venta_pagos WHERE venta_id = ?", (1,)
    )


def test_ventas_por_periodo_y_por_turno_usan_indice(con):
    plan = _plan(
        con,
        "SELECT v.* FROM ventas v WHERE v.estado = 'pagada' AND v.creado_en >= ? "
        "AND v.creado_en < ? ORDER BY v.id",
        ("2026-11-01", "2026-11-04"),
    )
    assert "idx_ventas_creado_en" in plan
    assert "idx_ventas_turno" in _plan(
        con, "SELECT v.* FROM ventas v WHERE v.turno_caja_id = ?", (1,)
    )


def test_la_cola_solo_indexa_lo_pendiente(con):
    plan = _plan(con, "SELECT * FROM cola_sincronizacion WHERE estado = 'pending' ORDER BY rowid")
    assert "idx_cola_pendientes" in plan


def test_por_periodo_incluye_ambos_extremos_con_los_dos_formatos_de_fecha(con):
    """El rango de texto reemplazo a date(creado_en): debe dar lo mismo en los bordes."""
    con.execute("INSERT INTO turnos_caja (id, usuario_id, fondo_inicial) VALUES (1, 1, 0)")
    for creado in (
        "2026-10-31 23:59:59",
        "2026-11-01 00:00:00",
        "2026-11-03T12:30:00",
        "2026-11-03 23:59:59",
        "2026-11-04 00:00:00",
    ):
        con.execute(
            "INSERT INTO ventas (turno_caja_id, usuario_id, estado, creado_en) "
            "VALUES (1, 1, 'pagada', ?)",
            (creado,),
        )
    repo = RepositorioVentasSQLite(con)
    dentro = repo.por_periodo(date(2026, 11, 1), date(2026, 11, 3))
    assert [v.creado_en.isoformat(sep=" ") for v in dentro] == [
        "2026-11-01 00:00:00",
        "2026-11-03 12:30:00",
        "2026-11-03 23:59:59",
    ]
