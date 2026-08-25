"""Pruebas del traductor de operaciones de sincronizacion a SQL de PostgreSQL.

Se testea el mapeo entidad -> (sql, params) sin necesidad de psycopg2 ni credenciales.
"""

import pytest

from pos.infraestructura.supabase.traductor import traducir_operacion


def _op(entidad, datos):
    return {"id_cliente": "uuid-1", "entidad": entidad, "operacion": "upsert", "datos": datos}


def test_traduce_producto_a_upsert_idempotente():
    sql, params = traducir_operacion(
        _op(
            "producto",
            {
                "codigo": "12345",
                "nombre": "Nueces",
                "precio": 8000,
                "unidad_venta": "granel",
                "categoria": "Frutos secos",
                "activo": True,
            },
        )
    )
    assert "INSERT INTO productos" in sql
    assert "ON CONFLICT (codigo) DO UPDATE" in sql  # idempotente por clave de negocio
    assert params == ("12345", "Nueces", 8000, "granel", "Frutos secos", True)


def test_traduce_producto_con_defaults():
    sql, params = traducir_operacion(
        _op(
            "producto", {"codigo": "1", "nombre": "Arroz", "precio": 1000, "unidad_venta": "unidad"}
        )
    )
    # categoria ausente -> None ; activo ausente -> True
    assert params == ("1", "Arroz", 1000, "unidad", None, True)


def test_traduce_existencia_a_upsert():
    sql, params = traducir_operacion(
        _op("existencia", {"codigo_producto": "12345", "cantidad": "2.750"})
    )
    assert "INSERT INTO existencias" in sql
    assert "ON CONFLICT (codigo_producto) DO UPDATE" in sql
    assert params == ("12345", "2.750")


def test_entidad_no_soportada_falla():
    with pytest.raises(ValueError):
        traducir_operacion(_op("venta", {"total": 1000}))
