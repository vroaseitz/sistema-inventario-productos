"""Deja lista la base de la demo en vivo: base nueva + proveedor y cliente ya creados.

Uso (desde la raiz del repo):  PYTHONPATH=src .venv/bin/python demo/preparar_demo.py
Borra demo/demo.db si existe y la crea de nuevo (datos ficticios).
"""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "demo" / "demo.db"
sys.path.insert(0, str(RAIZ / "src"))

for sufijo in ("", "-wal", "-shm"):
    Path(str(BASE) + sufijo).unlink(missing_ok=True)
subprocess.run(
    [sys.executable, str(RAIZ / "scripts" / "sembrar_demo_e2e.py"), str(BASE)], check=True
)

from pos.aplicacion.auditor import Auditor  # noqa: E402
from pos.aplicacion.casos_uso.gestionar_clientes import GestionarClientes  # noqa: E402
from pos.aplicacion.casos_uso.gestionar_proveedores import GestionarProveedores  # noqa: E402
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_facturas_compra import (  # noqa: E402
    RepositorioFacturasCompraSQLite,
)
from pos.infraestructura.sqlite.repositorio_proveedores import RepositorioProveedoresSQLite  # noqa: E402

con = crear_conexion(str(BASE))
cola = ColaSincronizacionSQLite(con)
auditor = Auditor(RepositorioAuditoriaSQLite(con), lambda: "admin", cola=cola)
GestionarProveedores(
    RepositorioProveedoresSQLite(con), RepositorioFacturasCompraSQLite(con), auditor, cola=cola
).crear("Frutos del Sur", "ventas@frutosdelsur.example")
GestionarClientes(RepositorioClientesSQLite(con), cola=cola).crear(
    "Juan Pérez", "+56 9 1234 5678", cupo=20000
)
con.commit()
con.close()
print("Demo lista: proveedor «Frutos del Sur» y cliente «Juan Pérez» (cupo $20.000) creados.")
