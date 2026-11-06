"""Prueba de humo de la sincronizacion contra el Supabase REAL (schema `pos`).

Publica una jornada minima con datos marcados ZZTEST (producto, stock, turno, movimiento,
venta con pago combinado), comprueba que quedaron bien, repite la publicacion para
confirmar que es idempotente y, al final, BORRA exactamente lo que creo (aunque falle).
No toca ninguna otra fila ni el schema `public`.

Uso (desde la raiz del repo, con SUPABASE_DB_URL en .env):
    PYTHONPATH=src python scripts/prueba_supabase_real.py
"""

# ruff: noqa: E501  (sentencias SQL largas en linea: se leen mejor completas)
from __future__ import annotations

import sys
from uuid import uuid4

from pos.infraestructura.config import Config
from pos.infraestructura.supabase.adaptador_supabase import AdaptadorSupabase

CODIGO = f"ZZTEST-{uuid4().hex[:8]}"
TURNO, VENTA = f"zztest-turno-{uuid4().hex}", f"zztest-venta-{uuid4().hex}"
OPERACIONES = [
    (
        "producto",
        f"zz-p-{uuid4().hex}",
        {"codigo": CODIGO, "nombre": "Prueba ZZTEST", "precio": 1000, "unidad_venta": "unidad"},
    ),
    ("existencia", f"zz-e-{uuid4().hex}", {"codigo_producto": CODIGO, "cantidad": "10"}),
    (
        "turno_abrir",
        f"zz-ta-{uuid4().hex}",
        {"uuid": TURNO, "fondo_inicial": 15000, "abierto_en": "2026-01-01T09:00:00"},
    ),
    (
        "movimiento_caja",
        f"zz-m-{uuid4().hex}",
        {
            "turno_uuid": TURNO,
            "tipo": "retiro",
            "monto": 500,
            "motivo": "ZZTEST",
            "creado_en": "2026-01-01T10:00:00",
        },
    ),
    (
        "venta",
        f"zz-v-{uuid4().hex}",
        {
            "uuid": VENTA,
            "turno_uuid": TURNO,
            "estado": "pagada",
            "creado_en": "2026-01-01T11:00:00",
            "detalles": [
                {"codigo": CODIGO, "cantidad": "2", "precio": 1000, "costo": 600, "descuento": 0}
            ],
            "pagos": [{"medio": "tarjeta", "monto": 1500}, {"medio": "efectivo", "monto": 500}],
        },
    ),
    ("turno_cerrar", f"zz-tc-{uuid4().hex}", {"uuid": TURNO, "cerrado_en": "2026-01-01T20:00:00"}),
]


def main() -> int:
    import psycopg2

    url = Config.desde_entorno().supabase_db_url
    if not url:
        print("Falta SUPABASE_DB_URL (ver config/.env.example)")
        return 2
    adaptador = AdaptadorSupabase(url)
    con = psycopg2.connect(url, connect_timeout=10)
    con.autocommit = True
    cur = con.cursor()

    def uno(sql: str, *p: object) -> object:
        cur.execute(sql, p)
        return cur.fetchone()[0]

    fallas: list[str] = []
    try:
        for vuelta in (1, 2):  # la 2.a repite todo: no debe duplicar nada
            for entidad, id_cliente, datos in OPERACIONES:
                adaptador.publicar(
                    {
                        "entidad": entidad,
                        "operacion": "upsert",
                        "id_cliente": id_cliente,
                        "datos": datos,
                    }
                )
            print(f"publicacion {vuelta}: OK ({len(OPERACIONES)} operaciones)")

        chequeos = {
            "1 producto": uno("SELECT count(*) FROM pos.producto WHERE codigo=%s", CODIGO) == 1,
            "stock 10": uno(
                "SELECT e.cantidad FROM pos.existencia e JOIN pos.producto p ON p.id=e.producto_id WHERE p.codigo=%s",
                CODIGO,
            )
            == 10,
            "1 turno cerrado": uno(
                "SELECT count(*) FROM pos.turno_caja WHERE id_cliente=%s AND cerrado_en IS NOT NULL",
                TURNO,
            )
            == 1,
            "1 movimiento": uno(
                "SELECT count(*) FROM pos.movimiento_caja m JOIN pos.turno_caja t ON t.id=m.turno_caja_id WHERE t.id_cliente=%s",
                TURNO,
            )
            == 1,
            "1 venta": uno("SELECT count(*) FROM pos.venta WHERE id_cliente=%s", VENTA) == 1,
            "1 linea": uno(
                "SELECT count(*) FROM pos.venta_detalle d JOIN pos.venta v ON v.id=d.venta_id WHERE v.id_cliente=%s",
                VENTA,
            )
            == 1,
            "2 pagos = $2.000": uno(
                "SELECT sum(monto) FROM pos.venta_pago p JOIN pos.venta v ON v.id=p.venta_id WHERE v.id_cliente=%s",
                VENTA,
            )
            == 2000,
            "ganancia generada = 800": uno(
                "SELECT d.ganancia FROM pos.venta_detalle d JOIN pos.venta v ON v.id=d.venta_id WHERE v.id_cliente=%s",
                VENTA,
            )
            == 800,
        }
        for nombre, ok in chequeos.items():
            print(f"  {'OK ' if ok else 'FALLA'} {nombre}")
            if not ok:
                fallas.append(nombre)
    finally:
        # Limpieza exacta de lo propio, en orden de dependencias.
        cur.execute(
            "DELETE FROM pos.venta_pago WHERE venta_id IN (SELECT id FROM pos.venta WHERE id_cliente=%s)",
            (VENTA,),
        )
        cur.execute(
            "DELETE FROM pos.venta_detalle WHERE venta_id IN (SELECT id FROM pos.venta WHERE id_cliente=%s)",
            (VENTA,),
        )
        cur.execute("DELETE FROM pos.venta WHERE id_cliente=%s", (VENTA,))
        cur.execute(
            "DELETE FROM pos.movimiento_caja WHERE turno_caja_id IN (SELECT id FROM pos.turno_caja WHERE id_cliente=%s)",
            (TURNO,),
        )
        cur.execute("DELETE FROM pos.turno_caja WHERE id_cliente=%s", (TURNO,))
        cur.execute(
            "DELETE FROM pos.existencia WHERE producto_id IN (SELECT id FROM pos.producto WHERE codigo=%s)",
            (CODIGO,),
        )
        cur.execute("DELETE FROM pos.producto WHERE codigo=%s", (CODIGO,))
        resto = uno(
            "SELECT (SELECT count(*) FROM pos.producto WHERE codigo LIKE 'ZZTEST-%%') + (SELECT count(*) FROM pos.venta WHERE id_cliente LIKE 'zztest-%%')"
        )
        print(f"limpieza: quedan {resto} filas ZZTEST")
        con.close()

    print("RESULTADO:", "TODO OK" if not fallas and resto == 0 else f"FALLAS {fallas}")
    return 0 if not fallas and resto == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
