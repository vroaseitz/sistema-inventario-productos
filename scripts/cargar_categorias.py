"""Carga la lista de categorias validada por la Product Owner (C-02, HU-PRD-10).

Uso:
    python scripts/cargar_categorias.py categorias.txt

El archivo lleva una categoria por linea (lineas vacias y las que empiezan con # se ignoran).
Agrega solo las que faltan: nunca renombra ni borra, porque los productos ya guardados
apuntan al id de su categoria. Se puede ejecutar varias veces.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pos.infraestructura.config import Config  # noqa: E402
from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_categorias import (  # noqa: E402
    RepositorioCategoriasSQLite,
)


def leer_nombres(ruta: Path) -> list[str]:
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return [x.strip() for x in lineas if x.strip() and not x.lstrip().startswith("#")]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    nombres = leer_nombres(Path(sys.argv[1]))
    conexion = crear_conexion(Config.desde_entorno().sqlite_path)
    crear_esquema(conexion)
    repo = RepositorioCategoriasSQLite(conexion)
    creadas = repo.sembrar(nombres)
    print(f"{creadas} categoria(s) nueva(s); en total hay {len(repo.listar())}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
