"""Pruebas del traductor de operaciones de sincronizacion a SQL de PostgreSQL.

Se testea el mapeo entidad -> [(sql, params)] sin psycopg2 ni credenciales. El efecto real
sobre un PostgreSQL se prueba en tests/integracion/test_sync_postgres.py.
"""

import pytest

from pos.infraestructura.supabase.traductor import traducir_operacion


def _op(entidad, datos, id_cliente="uuid-1"):
    return {"id_cliente": id_cliente, "entidad": entidad, "operacion": "upsert", "datos": datos}


def test_producto_es_upsert_por_codigo_en_schema_pos():
    ((sql, params),) = traducir_operacion(
        _op(
            "producto",
            {"codigo": "12345", "nombre": "Nueces", "precio": 8000, "unidad_venta": "granel"},
        )
    )
    assert "INSERT INTO pos.producto" in sql
    assert "ON CONFLICT (codigo) DO UPDATE" in sql
    # unidad_venta se pasa a mayusculas (el CHECK remoto exige UNIDAD/GRANEL); activo=True.
    assert params == ("12345", "Nueces", "GRANEL", 8000, True)


def test_existencia_es_upsert_resuelto_por_codigo():
    ((sql, params),) = traducir_operacion(
        _op("existencia", {"codigo_producto": "12345", "cantidad": "2.750"})
    )
    assert "INSERT INTO pos.existencia" in sql
    assert "ON CONFLICT (producto_id) DO UPDATE" in sql
    assert params == ("2.750", "12345")


def test_turno_abrir_es_idempotente_por_id_cliente():
    ((sql, params),) = traducir_operacion(
        _op(
            "turno_abrir", {"uuid": "t-1", "fondo_inicial": 15000, "abierto_en": "2026-10-28T09:00"}
        )
    )
    assert "ON CONFLICT (id_cliente) DO NOTHING" in sql
    assert params == ("t-1", 15000, "2026-10-28T09:00")


def test_turno_cerrar_no_reabre_ni_pisa_un_cierre_previo():
    ((sql, params),) = traducir_operacion(
        _op("turno_cerrar", {"uuid": "t-1", "cerrado_en": "2026-10-28T20:00"})
    )
    assert "cerrado_en IS NULL" in sql
    assert params == ("2026-10-28T20:00", "t-1")


def test_movimiento_caja_usa_el_id_de_la_operacion_para_idempotencia():
    ((sql, params),) = traducir_operacion(
        _op(
            "movimiento_caja",
            {
                "turno_uuid": "t-1",
                "tipo": "retiro",
                "monto": 3000,
                "motivo": "deposito",
                "creado_en": "2026-10-28T12:00",
            },
            id_cliente="mov-9",
        )
    )
    assert "ON CONFLICT (id_cliente) DO NOTHING" in sql
    assert params[0] == "mov-9" and params[-1] == "t-1"


def test_venta_va_en_una_sola_sentencia_con_lineas_y_pagos():
    datos = {
        "uuid": "v-1",
        "turno_uuid": "t-1",
        "estado": "pagada",
        "creado_en": "2026-10-28T10:00",
        "detalles": [
            {"codigo": "A", "cantidad": "2", "precio": 1990, "costo": 900, "descuento": 0},
            {"codigo": "B", "cantidad": "1", "precio": 2490, "costo": None},
        ],
        "pagos": [{"medio": "tarjeta", "monto": 2000}, {"medio": "efectivo", "monto": 4470}],
    }
    sentencias = traducir_operacion(_op("venta", datos))
    assert len(sentencias) == 1  # atomica: o entra completa o no entra
    sql, params = sentencias[0]
    assert "ON CONFLICT (id_cliente) DO NOTHING" in sql
    assert sql.count("%s") == len(params)
    assert params[:4] == ("v-1", "pagada", "2026-10-28T10:00", "t-1")
    assert params[9:14] == ("B", "1", 2490, None, 0)  # costo ausente -> NULL, descuento 0


def test_venta_sin_pagos_o_sin_lineas_no_se_traduce():
    base = {"uuid": "v", "turno_uuid": "t", "estado": "pagada", "creado_en": "x"}
    with pytest.raises(ValueError):
        traducir_operacion(
            _op("venta", {**base, "detalles": [], "pagos": [{"medio": "x", "monto": 1}]})
        )
    with pytest.raises(ValueError):
        traducir_operacion(
            _op(
                "venta",
                {**base, "detalles": [{"codigo": "A", "cantidad": "1", "precio": 1}], "pagos": []},
            )
        )


def test_entidad_no_soportada_falla():
    with pytest.raises(ValueError):
        traducir_operacion(_op("cliente", {"nombre": "x"}))
