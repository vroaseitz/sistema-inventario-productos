"""Base de demostracion para la prueba E2E grabada (docs/11-pruebas/guia-e2e-demo.md).

Crea una base SQLite NUEVA con lo que la guia da por cargado: la administradora y dos productos
(Almendras a granel, perecible, y Mix de frutos secos por unidad). No crea la vendedora, el
proveedor, el cliente ni ninguna venta: eso se hace durante la grabacion.

Uso (desde la raiz del repo):
    PYTHONPATH=src python scripts/sembrar_demo_e2e.py /ruta/demo.db

Usuaria: admin / admin-demo-2026 (datos ficticios, solo para esta demostracion).
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pos.aplicacion.casos_uso.gestionar_usuarios import GestionarUsuarios  # noqa: E402
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto  # noqa: E402
from pos.dominio.inventario import Existencia  # noqa: E402
from pos.dominio.productos import UnidadVenta  # noqa: E402
from pos.dominio.usuarios import Rol  # noqa: E402
from pos.infraestructura.seguridad.hasheador_bcrypt import HasheadorBcrypt  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_categorias import (  # noqa: E402
    RepositorioCategoriasSQLite,
)
from pos.infraestructura.sqlite.repositorio_existencias import (  # noqa: E402
    RepositorioExistenciasSQLite,
)
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite  # noqa: E402
from pos.infraestructura.sqlite.repositorio_usuarios import RepositorioUsuariosSQLite  # noqa: E402

ADMIN, CLAVE_ADMIN = "admin", "admin-demo-2026"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    ruta = Path(sys.argv[1])
    if ruta.exists():
        print(f"{ruta} ya existe: borrala o elige otra ruta (no se sobreescribe).")
        return 1
    con = crear_conexion(str(ruta))
    crear_esquema(con)
    GestionarUsuarios(RepositorioUsuariosSQLite(con), HasheadorBcrypt()).crear(
        ADMIN, CLAVE_ADMIN, CLAVE_ADMIN, Rol.ADMIN
    )
    categorias = RepositorioCategoriasSQLite(con)
    frutos = next(c for c in categorias.listar() if c.nombre == "Frutos secos y semillas")
    productos = RepositorioProductosSQLite(con)
    registrar = RegistrarProducto(productos, repositorio_categorias=categorias)
    # Almendras: a granel, perecible, aviso a 45 dias para que la alerta salte con un lote que
    # vence en 30. Sin stock: llega con la factura de compra de la escena 2.
    registrar.ejecutar(
        "ALM-GR", "Almendras a granel", 14990, UnidadVenta.GRANEL, frutos.id, 7900, True, 45
    )
    registrar.ejecutar(
        "MIX-250", "Mix de frutos secos 250 g", 3990, UnidadVenta.UNIDAD, frutos.id, 2200
    )
    RepositorioExistenciasSQLite(con).guardar(Existencia("MIX-250", Decimal("20")))
    con.commit()
    print(f"Base lista en {ruta}: usuaria {ADMIN} / {CLAVE_ADMIN}, 2 productos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
