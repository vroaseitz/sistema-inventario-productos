#!/usr/bin/env python3
"""Carga las categorias validadas por la Product Owner (C-02/C-04).

Uso:
    python scripts/cargar_categorias.py categorias.txt [ruta_bd]

El archivo debe traer una categoria por linea (lineas vacias y comentarios
con '#' se ignoran). Agrega las que faltan, NUNCA renombra ni borra las
existentes: los productos guardados conservan su categoria.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pos.infraestructura.sqlite.conexion import crear_conexion  # noqa: E402
from pos.infraestructura.sqlite.esquema import crear_esquema  # noqa: E402
from pos.infraestructura.sqlite.repositorio_productos import (  # noqa: E402
    RepositorioProductosSQLite,
)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1

    origen = Path(argv[1])
    if not origen.is_file():
        print(f"No existe el archivo: {origen}")
        return 1

    ruta_bd = argv[2] if len(argv) > 2 else "datos/pos_local.db"

    nombres: list[str] = []
    for linea in origen.read_text(encoding="utf-8").splitlines():
        nombre = linea.split("#", 1)[0].strip()
        if nombre:
            nombres.append(nombre)
    if not nombres:
        print("El archivo no contiene categorias.")
        return 1

    conexion = crear_conexion(ruta_bd)
    crear_esquema(conexion)
    repo = RepositorioProductosSQLite(conexion)

    existentes = {c.nombre for c in repo.listar_categorias()}
    nuevas = 0
    for nombre in nombres:
        if nombre.lower() in existentes:
            print(f"  ya existe, se omite: {nombre}")
            continue
        cat = repo.crear_categoria(nombre)
        existentes.add(cat.nombre)
        nuevas += 1
        print(f"  agregada: {cat.nombre} (id={cat.id})")

    conexion.commit()
    print(f"Listo: {nuevas} nuevas, {len(existentes)} en total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
