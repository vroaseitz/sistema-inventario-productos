"""Deja lista la base de la demo en vivo: base nueva + proveedor, cliente y jornada abierta.

Uso (desde la raiz del repo):  PYTHONPATH=src .venv/bin/python demo/preparar_demo.py
Borra demo/demo.db si existe y la crea de nuevo (datos ficticios). La jornada queda abierta con
$50.000 de fondo: ejecutarlo el MISMO DIA de la demo, para que la jornada sea de ese dia.
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
from pos.aplicacion.casos_uso.abrir_turno_caja import AbrirTurnoCaja  # noqa: E402
from pos.aplicacion.casos_uso.gestionar_clientes import GestionarClientes  # noqa: E402
from pos.aplicacion.casos_uso.gestionar_proveedores import GestionarProveedores  # noqa: E402
from pos.dominio.pagos import ConteoDenominaciones  # noqa: E402
from pos.dominio.value_objects import Dinero  # noqa: E402
from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_clientes import RepositorioClientesSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_facturas_compra import (  # noqa: E402
    RepositorioFacturasCompraSQLite,
)
from pos.infraestructura.sqlite.repositorio_proveedores import RepositorioProveedoresSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_turnos_caja import RepositorioTurnosCajaSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_usuarios import RepositorioUsuariosSQLite  # noqa: E402

con = crear_conexion(str(BASE))
cola = ColaSincronizacionSQLite(con)
auditor = Auditor(RepositorioAuditoriaSQLite(con), lambda: "admin", cola=cola)
GestionarProveedores(
    RepositorioProveedoresSQLite(con), RepositorioFacturasCompraSQLite(con), auditor, cola=cola
).crear("Frutos del Sur", "ventas@frutosdelsur.example")
GestionarClientes(RepositorioClientesSQLite(con), cola=cola).crear(
    "Juan Pérez", "+56 9 1234 5678", cupo=20000
)
# Jornada abierta con el fondo contado: 2 billetes de $20.000 y 1 de $10.000.
admin = RepositorioUsuariosSQLite(con).obtener_por_nombre("admin")
conteo = ConteoDenominaciones({20000: 2, 10000: 1})
AbrirTurnoCaja(RepositorioTurnosCajaSQLite(con), cola=cola).ejecutar(
    usuario_id=admin.id, fondo_inicial=Dinero(conteo.total), composicion_fondo_inicial=conteo
)
con.commit()
con.close()
print("Demo lista: proveedor «Frutos del Sur», cliente «Juan Pérez» (cupo $20.000)")
print("y jornada abierta con $50.000 de fondo.")
