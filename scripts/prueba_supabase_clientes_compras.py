"""Prueba de humo contra el Supabase REAL: clientes, credito, proveedores, facturas y auditoria.

Requiere la migracion 008 aplicada (`python scripts/verificar_supabase.py` lo confirma). Publica
datos marcados ZZTEST con las MISMAS funciones que usa la app para encolar (asi se prueba lo real,
no una copia), repite la publicacion para confirmar que no duplica, comprueba el resultado y al
final BORRA exactamente lo que creo (aunque falle). No toca ninguna otra fila.

Uso (desde la raiz del repo, con SUPABASE_DB_URL en .env):
    PYTHONPATH=src python scripts/prueba_supabase_clientes_compras.py
"""

# ruff: noqa: E501  (sentencias SQL largas en linea: se leen mejor completas)
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from uuid import uuid4

from pos.aplicacion.sincronizacion import (
    encolar_auditoria,
    encolar_cliente,
    encolar_factura_compra,
    encolar_movimiento_cliente,
    encolar_producto,
    encolar_proveedor,
)
from pos.dominio.clientes import Cliente, MovimientoCliente, TipoMovimientoCliente
from pos.dominio.compras import FacturaCompra, LineaFactura
from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.config import Config
from pos.infraestructura.supabase.adaptador_supabase import AdaptadorSupabase

SUFIJO = uuid4().hex[:8]
CODIGO = f"ZZTEST-{SUFIJO}"
PROVEEDOR = f"ZZTEST proveedor {SUFIJO}"
NUMERO = f"ZZ-{SUFIJO}"
CLIENTE_ID = 987_000_000 + int(SUFIJO[:5], 16) % 1_000_000  # id local que no choca con uno real
CLIENTE_CLAVE = f"cliente:{CLIENTE_ID}"
AUDITORIA_ID = 987_000_000 + int(SUFIJO[3:], 16) % 1_000_000
AUDITORIA_CLAVE = f"auditoria:{AUDITORIA_ID}"


class ColaEnMemoria:
    """Junta lo que la app encolaria, para publicarlo tal cual."""

    def __init__(self) -> None:
        self.operaciones: list[dict] = []

    def encolar(self, entidad: str, operacion: str, datos: dict, id_cliente: str) -> None:
        self.operaciones.append(
            {"entidad": entidad, "operacion": operacion, "datos": datos, "id_cliente": id_cliente}
        )


def armar_operaciones() -> list[dict]:
    cola = ColaEnMemoria()
    cliente = Cliente(f"ZZTEST cliente {SUFIJO}", "+56 9 0000 0000", "", "prueba", True, CLIENTE_ID)
    producto = Producto(CODIGO, "Prueba ZZTEST", Dinero(1000), categoria_id=1)
    encolar_producto(cola, producto, None)
    encolar_cliente(cola, cliente)
    for tipo, monto, medio, detalle in (
        (TipoMovimientoCliente.CONSUMO, 5000, None, "Consumo ZZTEST"),
        (TipoMovimientoCliente.ABONO, 2000, "transferencia", "Pago ZZTEST"),
        (TipoMovimientoCliente.ABONO, 1000, "descuento", "Descuento ZZTEST"),
    ):
        movimiento = MovimientoCliente(
            CLIENTE_ID, tipo, monto, date(2026, 1, 1), detalle, medio=medio
        )
        encolar_movimiento_cliente(cola, cliente, movimiento)
    encolar_proveedor(cola, PROVEEDOR, "zz@test.cl")
    encolar_factura_compra(
        cola,
        FacturaCompra(
            PROVEEDOR,
            NUMERO,
            date(2026, 1, 1),
            12_000,
            2_280,
            [LineaFactura(CODIGO, Decimal("10"), 1200, codigo_lote="L-ZZ")],
        ),
    )
    encolar_auditoria(
        cola,
        AUDITORIA_ID,
        "2026-01-01T10:00:00",
        "zztest",
        "Prueba ZZTEST",
        "registro",
        "antes",
        "despues",
        "{}",
    )
    return cola.operaciones


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

    operaciones = armar_operaciones()
    fallas: list[str] = []
    try:
        for vuelta in (1, 2):  # la 2.a repite todo: no debe duplicar nada
            for operacion in operaciones:
                adaptador.publicar(operacion)
            print(f"publicacion {vuelta}: OK ({len(operaciones)} operaciones)")

        chequeos = {
            "1 cliente con credito": uno(
                "SELECT count(*) FROM pos.cliente WHERE id_cliente=%s AND tiene_credito AND activo",
                CLIENTE_CLAVE,
            )
            == 1,
            "3 movimientos": uno(
                "SELECT count(*) FROM pos.movimiento_credito m JOIN pos.cliente c ON c.id=m.cliente_id WHERE c.id_cliente=%s",
                CLIENTE_CLAVE,
            )
            == 3,
            "saldo = 5000 - 2000 - 1000": uno(
                "SELECT sum(CASE m.tipo WHEN 'cargo' THEN m.monto ELSE -m.monto END) FROM pos.movimiento_credito m JOIN pos.cliente c ON c.id=m.cliente_id WHERE c.id_cliente=%s",
                CLIENTE_CLAVE,
            )
            == Decimal(2000),
            "1 descuento asentado": uno(
                "SELECT count(*) FROM pos.movimiento_credito m JOIN pos.cliente c ON c.id=m.cliente_id WHERE c.id_cliente=%s AND m.medio='descuento'",
                CLIENTE_CLAVE,
            )
            == 1,
            "1 proveedor": uno(
                "SELECT count(*) FROM pos.proveedor WHERE lower(nombre)=lower(%s)", PROVEEDOR
            )
            == 1,
            "1 factura": uno(
                "SELECT count(*) FROM pos.factura_compra f JOIN pos.proveedor p ON p.id=f.proveedor_id WHERE lower(p.nombre)=lower(%s) AND f.numero_factura=%s",
                PROVEEDOR,
                NUMERO,
            )
            == 1,
            "1 linea de factura con su lote": uno(
                "SELECT count(*) FROM pos.factura_compra_detalle d JOIN pos.factura_compra f ON f.id=d.factura_id JOIN pos.proveedor p ON p.id=f.proveedor_id WHERE lower(p.nombre)=lower(%s) AND f.numero_factura=%s AND d.codigo_lote='L-ZZ'",
                PROVEEDOR,
                NUMERO,
            )
            == 1,
            "1 auditoria": uno(
                "SELECT count(*) FROM pos.auditoria WHERE id_cliente=%s", AUDITORIA_CLAVE
            )
            == 1,
        }
        for nombre, ok in chequeos.items():
            print(f"  {'OK ' if ok else 'FALLA'} {nombre}")
            if not ok:
                fallas.append(nombre)
    finally:
        # Limpieza exacta de lo propio, en orden de dependencias.
        cur.execute(
            "DELETE FROM pos.factura_compra_detalle WHERE factura_id IN (SELECT f.id FROM pos.factura_compra f JOIN pos.proveedor p ON p.id=f.proveedor_id WHERE lower(p.nombre)=lower(%s))",
            (PROVEEDOR,),
        )
        cur.execute(
            "DELETE FROM pos.factura_compra WHERE proveedor_id IN (SELECT id FROM pos.proveedor WHERE lower(nombre)=lower(%s))",
            (PROVEEDOR,),
        )
        cur.execute("DELETE FROM pos.proveedor WHERE lower(nombre)=lower(%s)", (PROVEEDOR,))
        cur.execute(
            "DELETE FROM pos.movimiento_credito WHERE cliente_id IN (SELECT id FROM pos.cliente WHERE id_cliente=%s)",
            (CLIENTE_CLAVE,),
        )
        cur.execute("DELETE FROM pos.cliente WHERE id_cliente=%s", (CLIENTE_CLAVE,))
        cur.execute("DELETE FROM pos.auditoria WHERE id_cliente=%s", (AUDITORIA_CLAVE,))
        cur.execute("DELETE FROM pos.producto WHERE codigo=%s", (CODIGO,))
        restos = sum(
            uno(sql, valor)
            for sql, valor in (
                ("SELECT count(*) FROM pos.cliente WHERE id_cliente=%s", CLIENTE_CLAVE),
                ("SELECT count(*) FROM pos.proveedor WHERE lower(nombre)=lower(%s)", PROVEEDOR),
                ("SELECT count(*) FROM pos.auditoria WHERE id_cliente=%s", AUDITORIA_CLAVE),
                ("SELECT count(*) FROM pos.producto WHERE codigo=%s", CODIGO),
            )
        )
        print(f"limpieza: quedan {restos} filas ZZTEST")
        con.close()
        if restos:
            fallas.append("limpieza incompleta")

    print("RESULTADO:", "TODO OK" if not fallas else f"FALLAS: {', '.join(fallas)}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
