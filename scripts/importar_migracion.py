"""Importa productos y clientes del sistema antiguo (QA 18-11, migracion de datos).

Uso (desde la raiz del repo):
    PYTHONPATH=src python scripts/importar_migracion.py --productos productos_a_migrar.csv \
        --clientes clientes_a_migrar_PRIVADO.csv [--simulacro]

La base es la de POS_SQLITE_PATH (igual que la aplicacion). Con --simulacro se prueba todo sobre una
copia: la base real no se modifica. Se puede ejecutar dos veces: lo que ya existe se omite.

Los CSV de clientes son datos personales: NO se suben al repositorio y se borran al terminar.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pos.aplicacion.auditor import Auditor  # noqa: E402
from pos.aplicacion.casos_uso.migrar_datos_legados import (  # noqa: E402
    COLUMNAS_CLIENTES,
    COLUMNAS_PRODUCTOS,
    CONTACTO_PENDIENTE,
    ErrorArchivo,
    MigrarClientes,
    MigrarProductos,
    leer_csv,
)
from pos.aplicacion.registro_movimientos import RegistroMovimientos  # noqa: E402
from pos.infraestructura.config import Config  # noqa: E402
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_categorias import (  # noqa: E402
    RepositorioCategoriasSQLite,
)
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_existencias import (  # noqa: E402
    RepositorioExistenciasSQLite,
)
from pos.infraestructura.sqlite.repositorio_movimientos import (  # noqa: E402
    RepositorioMovimientosSQLite,
)
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite  # noqa: E402

USUARIO = "migración"


def fin_de_mes_anterior(hoy: date) -> date:
    """El saldo antiguo se fecha antes del ciclo en curso: asi no cuenta como consumo del mes
    (y no recibe el 20 % de descuento del credito familiar de este mes)."""
    return date(hoy.year, hoy.month, 1) - timedelta(days=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Migracion de productos y clientes")
    ap.add_argument("--productos", type=Path)
    ap.add_argument("--clientes", type=Path)
    ap.add_argument("--simulacro", action="store_true", help="probar y deshacer")
    ap.add_argument("--fecha-saldo", type=date.fromisoformat, default=None, metavar="AAAA-MM-DD")
    ap.add_argument("--contacto-pendiente", default=CONTACTO_PENDIENTE)
    ap.add_argument("--sin-cola", action="store_true", help="no encolar para Supabase")
    args = ap.parse_args(argv)
    if not (args.productos or args.clientes):
        ap.error("indica --productos y/o --clientes")

    try:
        filas_p = leer_csv(args.productos, COLUMNAS_PRODUCTOS) if args.productos else None
        filas_c = leer_csv(args.clientes, COLUMNAS_CLIENTES) if args.clientes else None
    except ErrorArchivo as exc:
        print(f"Error: {exc}")
        return 2

    ruta_db = Config.desde_entorno().sqlite_path
    con = crear_conexion(ruta_db)
    crear_esquema(con)
    if args.simulacro:
        # Algunos repositorios confirman solos, asi que no hay una transaccion que deshacer:
        # el simulacro corre sobre una copia en memoria y la base real no se toca.
        copia = crear_conexion(":memory:")
        con.backup(copia)
        con.close()
        con = copia
    cola = None if args.sin_cola else ColaSincronizacionSQLite(con)
    auditor = Auditor(RepositorioAuditoriaSQLite(con), lambda: USUARIO, cola=cola)
    resumenes = []
    try:
        if filas_p is not None:
            resumenes.append(
                MigrarProductos(
                    RepositorioProductosSQLite(con),
                    RepositorioCategoriasSQLite(con),
                    RepositorioExistenciasSQLite(con),
                    RegistroMovimientos(RepositorioMovimientosSQLite(con), lambda: USUARIO),
                    cola,
                    auditor,
                ).ejecutar(filas_p)
            )
        if filas_c is not None:
            fecha = args.fecha_saldo or fin_de_mes_anterior(date.today())
            resumenes.append(
                MigrarClientes(
                    RepositorioClientesSQLite(con),
                    lambda: fecha,
                    cola,
                    auditor,
                    args.contacto_pendiente,
                ).ejecutar(filas_c)
            )
    finally:
        con.close()
    print(f"Base: {ruta_db} ({'SIMULACRO, nada se guardó' if args.simulacro else 'guardado'})")
    for r in resumenes:
        print("\n".join(r.lineas()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
