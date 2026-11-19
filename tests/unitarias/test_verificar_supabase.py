"""El comparador de esquema (scripts/verificar_supabase.py) entiende las migraciones reales."""

import importlib.util
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "scripts" / "verificar_supabase.py"
_spec = importlib.util.spec_from_file_location("verificar_supabase", RUTA)
verificar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verificar)


def test_lee_las_tablas_y_columnas_que_dejan_las_migraciones():
    esperado = verificar.columnas_esperadas()
    assert {"producto", "categoria", "venta", "venta_detalle", "lote", "turno_caja"} <= set(
        esperado
    )
    # 002 crea la tabla; 004 agrega codigo e id_cliente; 007 agrega stock_minimo, nota y mas.
    assert {"nombre", "precio_venta", "codigo", "stock_minimo"} <= esperado["producto"]
    assert "id_cliente" in esperado["venta"] and "nota" in esperado["venta"]
    assert "motivo_descuento" in esperado["venta_detalle"]
    assert {"activa"} <= esperado["categoria"] and {"codigo_lote"} <= esperado["lote"]
    # Las restricciones no son columnas.
    assert not {"constraint", "primary", "foreign", "unique", "check"} & esperado["producto"]


def test_comparar_dice_que_falta_y_que_sobra():
    esperado = {"producto": {"id", "codigo", "stock_minimo"}, "venta": {"id", "nota"}}
    real = {"producto": {"id", "codigo"}, "otra": {"x"}}  # sin 007 y sin la tabla venta
    faltan_tablas, faltan_columnas, sobran = verificar.comparar(esperado, real)
    assert faltan_tablas == ["venta"]
    assert faltan_columnas == ["producto.stock_minimo"]
    assert sobran == ["otra"]
    assert verificar.comparar(esperado, esperado) == ([], [], [])


def test_las_sentencias_con_parentesis_anidados_no_inventan_columnas():
    sql_tabla = "CREATE TABLE t (a INT CHECK (a > 0), b NUMERIC(12, 2) NOT NULL, UNIQUE (a, b))"
    cuerpo = verificar._cuerpo_entre_parentesis(sql_tabla, 0)
    partes = verificar._partes_de_primer_nivel(cuerpo)
    assert [p.split()[0] for p in partes] == ["a", "b", "UNIQUE"]


def test_la_001_esta_superada_por_la_002_y_no_se_espera_en_supabase():
    """La 002 dice que supera a la 001: productos/existencias/cola no deben existir en `pos`."""
    esperado = verificar.columnas_esperadas()
    assert not {"productos", "existencias", "cola_sincronizacion"} & set(esperado)
    assert "producto" in esperado and "existencia" in esperado
