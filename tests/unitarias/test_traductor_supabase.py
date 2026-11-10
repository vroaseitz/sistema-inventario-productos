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
    # Sin costo ni perecible en la operacion (cola vieja): costo None, no cargado, no perecible.
    assert params == ("12345", "Nueces", "GRANEL", 8000, True, None, False, False, None, None)


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
    assert params[:5] == ("v-1", "pagada", "2026-10-28T10:00", None, "t-1")  # nota ausente -> NULL
    # costo ausente -> NULL, descuento 0, motivo ausente -> NULL
    assert params[11:17] == ("B", "1", 2490, None, 0, None)


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
        traducir_operacion(_op("usuario", {"nombre": "x"}))  # los usuarios no viajan a la nube


def test_producto_lleva_costo_perecible_dias_y_minimo():
    ((_, params),) = traducir_operacion(
        _op(
            "producto",
            {
                "codigo": "YOG",
                "nombre": "Yogurt",
                "precio": 2000,
                "unidad_venta": "unidad",
                "costo": 1200,
                "perecible": True,
                "dias_aviso": 7,
                "stock_minimo": 6,
            },
        )
    )
    assert params[-5:] == (1200, True, True, 7, 6)  # costo, cargado, perecible, dias, minimo


def test_categoria_se_envia_con_su_estado():
    ((sql, params),) = traducir_operacion(_op("categoria", {"nombre": "Mascotas", "activa": False}))
    assert "pos.categoria" in sql and "ON CONFLICT (nombre) DO UPDATE" in sql
    assert params == ("Mascotas", False)


def test_categoria_renombrar_no_pisa_un_nombre_existente():
    ((sql, params),) = traducir_operacion(
        _op("categoria_renombrar", {"anterior": "Viejo", "nuevo": "Nuevo"})
    )
    assert "NOT EXISTS" in sql
    assert params == ("Nuevo", "Viejo", "Nuevo")


def test_categoria_eliminar_nunca_borra_una_con_productos():
    ((sql, params),) = traducir_operacion(_op("categoria_eliminar", {"nombre": "Varios"}))
    assert "DELETE FROM pos.categoria" in sql and "NOT EXISTS" in sql
    assert params == ("Varios",)


def test_venta_lleva_nota_y_motivo_del_descuento():
    ((sql, params),) = traducir_operacion(
        _op(
            "venta",
            {
                "uuid": "v1",
                "turno_uuid": "t1",
                "estado": "pagada",
                "creado_en": "2026-11-02T22:08:00",
                "nota": "Para regalo",
                "detalles": [
                    {
                        "codigo": "A",
                        "cantidad": "1",
                        "precio": 1000,
                        "costo": 600,
                        "descuento": 100,
                        "motivo_descuento": "Cortesía",
                    }
                ],
                "pagos": [{"medio": "efectivo", "monto": 900}],
            },
        )
    )
    assert "nota" in sql and "motivo_descuento" in sql
    assert params[3] == "Para regalo"  # nota, antes del uuid del turno
    assert params[4] == "t1"
    assert "Cortesía" in params


def test_lote_lleva_el_codigo_impreso():
    ((_, params),) = traducir_operacion(
        _op(
            "lote",
            {
                "uuid": "l1",
                "codigo_producto": "YOG",
                "fecha_vencimiento": "2026-12-01",
                "saldo": "10",
                "codigo_lote": "LT-77",
            },
        )
    )
    assert params == ("l1", "2026-12-01", "10", "LT-77", "YOG")


def test_cambio_de_codigo_renombra_el_producto_y_no_pisa_a_otro():
    """CA-19: el destino renombra el producto; si el codigo nuevo ya existe, no hace nada."""
    ((sql, params),) = traducir_operacion(
        _op("producto_codigo", {"anterior": "111", "nuevo": "222"})
    )
    assert sql.startswith("UPDATE pos.producto SET codigo = %s WHERE codigo = %s")
    assert "NOT EXISTS" in sql  # reintentar o chocar con otro codigo es inofensivo
    assert params == ("222", "111", "222")


CLIENTE = {
    "id": "cliente:7",
    "nombre": "Carolina Muñoz",
    "telefono": "+56 9 1111 1111",
    "correo": "",
    "observaciones": "Familia",
    "activo": True,
    "cupo": 150000,
}


def test_cliente_es_upsert_por_su_id_y_tiene_credito():
    ((sql, params),) = traducir_operacion(_op("cliente", CLIENTE))
    assert "INSERT INTO pos.cliente" in sql and "ON CONFLICT (id_cliente) DO UPDATE" in sql
    assert "cupo_credito" in sql  # CL-01: el cupo viaja con el cliente
    assert params == ("cliente:7", "Carolina Muñoz", "+56 9 1111 1111", "", "Familia", True, 150000)


def test_el_consumo_es_un_cargo_y_lleva_al_cliente_por_si_aun_no_llego():
    datos = {
        "uuid": "mov-1",
        "cliente": CLIENTE,
        "tipo": "consumo",
        "monto": 5950,
        "fecha": "2026-11-05",
        "detalle": "Venta N° 3 · 1 producto",
        "medio": None,
        "venta_uuid": "venta-uuid-3",
    }
    sentencias = traducir_operacion(_op("movimiento_cliente", datos))
    assert "INSERT INTO pos.cliente" in sentencias[0][0]  # el cliente entra primero
    sql, params = sentencias[1]
    assert (
        "INSERT INTO pos.movimiento_credito" in sql and "ON CONFLICT (id_cliente) DO NOTHING" in sql
    )
    assert params[:4] == ("mov-1", "venta-uuid-3", "cargo", 5950)  # consumo -> cargo
    assert params[-1] == "cliente:7"


def test_el_abono_y_el_descuento_conservan_su_tipo_y_medio():
    datos = {
        "uuid": "mov-2",
        "cliente": CLIENTE,
        "tipo": "abono",
        "monto": 22054,
        "fecha": "2026-11-05",
        "detalle": "Descuento crédito familiar 11-2026",
        "medio": "descuento",
        "venta_uuid": None,
    }
    _, (_, params) = traducir_operacion(_op("movimiento_cliente", datos))
    assert params[2] == "abono" and params[5] == "descuento" and params[1] is None


def test_proveedor_no_se_duplica_aunque_cambie_la_mayuscula():
    ((sql, params),) = traducir_operacion(
        _op("proveedor", {"nombre": "Sur Natural", "contacto": ""})
    )
    assert "ON CONFLICT (lower(nombre))" in sql and params == ("Sur Natural", "")


def test_factura_va_en_una_sola_sentencia_con_el_proveedor_asegurado_antes():
    datos = {
        "proveedor": "Sur Natural",
        "numero": "F-1001",
        "fecha": "2026-11-05",
        "neto": 156000,
        "impuestos": 29640,
        "estado": "confirmada",
        "lineas": [
            {
                "codigo": "A",
                "cantidad": "20",
                "costo": 2500,
                "costo_anterior": None,
                "vence": None,
                "lote": "",
            },
            {
                "codigo": "B",
                "cantidad": "24",
                "costo": 1500,
                "costo_anterior": 1400,
                "vence": "2026-11-08",
                "lote": "L-1",
            },
        ],
    }
    asegurar, (sql, params) = traducir_operacion(_op("factura_compra", datos))
    assert "INSERT INTO pos.proveedor" in asegurar[0] and "DO NOTHING" in asegurar[0]
    assert "ON CONFLICT (proveedor_id, numero_factura) DO NOTHING" in sql  # reintentar no duplica
    assert sql.count("%s") == len(params) == 6 + 2 * 6  # 6 de la cabecera + 6 por linea
    assert params[:6] == ("F-1001", "2026-11-05", 156000, 29640, "confirmada", "Sur Natural")
    with pytest.raises(ValueError):
        traducir_operacion(_op("factura_compra", {**datos, "lineas": []}))


def test_auditoria_se_guarda_una_vez_por_su_id():
    datos = {
        "id": "auditoria:12",
        "fecha": "2026-11-05T10:00:00",
        "usuario": "admin",
        "accion": "Cambio de precio",
        "registro": "Miel (7801)",
        "antes": "$4.990",
        "despues": "$5.490",
        "detalle": "{}",
    }
    ((sql, params),) = traducir_operacion(_op("auditoria", datos))
    assert "ON CONFLICT (id_cliente) DO NOTHING" in sql and "to_jsonb" in sql
    assert params[0] == "auditoria:12" and params[2] == "admin" and params[-1] == datos["fecha"]
