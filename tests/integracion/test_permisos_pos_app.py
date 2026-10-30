"""El rol pos_app puede operar TODAS las tablas del schema pos (PostgreSQL real).

Se omite sin POS_TEST_PG_URL (ver test_sync_postgres.py). Detecta justo el fallo del
premortem: una tabla nueva sin politica RLS/GRANT que rompe la sincronizacion en silencio.
"""

import os
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

PG_URL = os.environ.get("POS_TEST_PG_URL")
MIGRACIONES = Path(__file__).resolve().parents[2] / "database" / "migraciones"
pytestmark = pytest.mark.skipif(not PG_URL, reason="define POS_TEST_PG_URL")

CONSULTA_SIN_ACCESO = """
SELECT t.tablename FROM pg_tables t
WHERE t.schemaname = 'pos'
  AND (
    NOT has_table_privilege('pos_app', format('pos.%I', t.tablename),
                            'SELECT,INSERT,UPDATE,DELETE')
    OR NOT EXISTS (SELECT 1 FROM pg_policies p
                   WHERE p.schemaname = 'pos' AND p.tablename = t.tablename
                     AND 'pos_app' = ANY (p.roles))
  )
ORDER BY 1
"""


@pytest.fixture
def pg():
    if "supabase" in PG_URL.lower():
        pytest.fail("Este test BORRA el schema pos: nunca apuntarlo a Supabase.")
    con = psycopg2.connect(PG_URL)
    con.autocommit = True
    cur = con.cursor()
    cur.execute("DROP SCHEMA IF EXISTS pos CASCADE; CREATE SCHEMA pos; SET search_path TO pos;")
    cur.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='pos_app') "
        "THEN CREATE ROLE pos_app LOGIN PASSWORD 'test'; END IF; END $$;"
    )
    for nombre in sorted(MIGRACIONES.glob("[0-9]*.sql")):
        if nombre.name.startswith("001"):
            continue  # borrador antiguo: lo reemplaza 002
        cur.execute(nombre.read_text())
    cur.execute("RESET search_path;")
    yield cur
    cur.execute("DROP SCHEMA IF EXISTS pos CASCADE;")
    con.close()


def test_pos_app_tiene_acceso_y_politica_en_todas_las_tablas(pg):
    pg.execute(CONSULTA_SIN_ACCESO)
    assert pg.fetchall() == []


def test_el_detector_ve_una_tabla_nueva_sin_politica_y_la_funcion_la_arregla(pg):
    pg.execute("CREATE TABLE pos.tabla_nueva (id int)")
    pg.execute(CONSULTA_SIN_ACCESO)
    assert [f[0] for f in pg.fetchall()] == ["tabla_nueva"]  # el detector funciona
    pg.execute("SELECT pos.aplicar_permisos_pos_app()")
    pg.execute(CONSULTA_SIN_ACCESO)
    assert pg.fetchall() == []


def test_pos_app_opera_de_verdad_y_no_ve_public(pg):
    url = PG_URL.replace("postgres:postgres@", "pos_app:test@", 1)
    con = psycopg2.connect(url)
    con.autocommit = True
    cur = con.cursor()
    cur.execute("INSERT INTO pos.categoria (nombre) VALUES ('Prueba') ON CONFLICT DO NOTHING")
    cur.execute("SELECT count(*) FROM pos.categoria WHERE nombre = 'Prueba'")
    assert cur.fetchone()[0] == 1
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("CREATE TABLE public.zz_prueba (i int)")
    con.close()
