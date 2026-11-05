"""Compara el Supabase REAL (schema `pos`) con las migraciones del repo. SOLO LECTURA.

Dice que tablas y columnas faltan, cuales sobran, y cuantas filas hay en cada tabla. No escribe
nada: la sesion se abre en modo solo lectura y solo ejecuta SELECT. Sirve para saber, antes de la
marcha blanca, si faltan migraciones por pegar en el SQL Editor (p. ej. la 007).

Uso (desde la raiz del repo, con SUPABASE_DB_URL en .env):
    python scripts/verificar_supabase.py

Sale con codigo 0 si no falta nada, 1 si faltan tablas o columnas, 2 si no pudo conectarse.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MIGRACIONES = RAIZ / "database" / "migraciones"
_NO_COLUMNAS = {"CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "EXCLUDE", "LIKE"}
# La 002 declara que SUPERA a la 001 (borrador de 3 tablas con otro modelo): sus tablas
# (productos, existencias, cola_sincronizacion) no deben existir en el schema `pos`.
_SUPERADAS = {"001_esquema_inicial.sql"}


def _sin_comentarios(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", " ", sql)


def _partes_de_primer_nivel(cuerpo: str) -> list[str]:
    """Parte `cuerpo` por las comas que no estan dentro de parentesis."""
    partes, nivel, actual = [], 0, []
    for caracter in cuerpo:
        nivel += caracter == "("
        nivel -= caracter == ")"
        if caracter == "," and nivel == 0:
            partes.append("".join(actual))
            actual = []
        else:
            actual.append(caracter)
    partes.append("".join(actual))
    return [p.strip() for p in partes if p.strip()]


def _cuerpo_entre_parentesis(sql: str, desde: int) -> str:
    """Texto entre el primer `(` desde `desde` y su `)` de cierre."""
    inicio = sql.index("(", desde)
    nivel = 0
    for i in range(inicio, len(sql)):
        nivel += sql[i] == "("
        nivel -= sql[i] == ")"
        if nivel == 0:
            return sql[inicio + 1 : i]
    raise ValueError("parentesis sin cerrar")


def columnas_esperadas(carpeta: Path = MIGRACIONES) -> dict[str, set[str]]:
    """Tablas y columnas que dejan las migraciones .sql aplicadas en orden (001, 002, ...)."""
    tablas: dict[str, set[str]] = {}
    for archivo in sorted(carpeta.glob("[0-9]*.sql")):
        if archivo.name in _SUPERADAS:
            continue
        sql = _sin_comentarios(archivo.read_text(encoding="utf-8"))
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:pos\.)?(\w+)\s*\(", sql, re.I
        ):
            columnas = set()
            for parte in _partes_de_primer_nivel(_cuerpo_entre_parentesis(sql, m.start())):
                primera = parte.split()[0].strip('"')
                if primera.upper() not in _NO_COLUMNAS:
                    columnas.add(primera.lower())
            tablas.setdefault(m.group(1).lower(), set()).update(columnas)
        for m in re.finditer(
            r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:pos\.)?(\w+)\s+([^;]+);", sql, re.I
        ):
            tabla = m.group(1).lower()
            for agregada in re.finditer(
                r"ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?\"?(\w+)", m.group(2), re.I
            ):
                tablas.setdefault(tabla, set()).add(agregada.group(1).lower())
            for quitada in re.finditer(
                r"DROP\s+COLUMN\s+(?:IF\s+EXISTS\s+)?\"?(\w+)", m.group(2), re.I
            ):
                tablas.get(tabla, set()).discard(quitada.group(1).lower())
    return tablas


def comparar(
    esperado: dict[str, set[str]], real: dict[str, set[str]]
) -> tuple[list[str], list[str], list[str]]:
    """(tablas que faltan, columnas que faltan como 'tabla.col', tablas que sobran)."""
    faltan_tablas = sorted(t for t in esperado if t not in real)
    faltan_columnas = sorted(
        f"{t}.{c}" for t, cols in esperado.items() if t in real for c in sorted(cols - real[t])
    )
    sobran = sorted(t for t in real if t not in esperado)
    return faltan_tablas, faltan_columnas, sobran


def leer_esquema_real(url: str) -> tuple[dict[str, set[str]], dict[str, int]]:
    import psycopg2

    conexion = psycopg2.connect(url, connect_timeout=15)
    try:
        conexion.set_session(readonly=True, autocommit=True)  # nada de esto puede escribir
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'pos' ORDER BY table_name, ordinal_position"
        )
        real: dict[str, set[str]] = {}
        for tabla, columna in cursor.fetchall():
            real.setdefault(tabla, set()).add(columna)
        filas = {}
        for tabla in sorted(real):
            cursor.execute(f'SELECT count(*) FROM pos."{tabla}"')
            filas[tabla] = cursor.fetchone()[0]
        return real, filas
    finally:
        conexion.close()


def main() -> int:
    sys.path.insert(0, str(RAIZ / "src"))
    from pos.infraestructura.config import Config

    url = Config.desde_entorno().supabase_db_url
    if not url or "<" in url:
        print("Falta SUPABASE_DB_URL en .env (o aun tiene el texto <PASSWORD> sin reemplazar).")
        return 2
    try:
        real, filas = leer_esquema_real(url)
    except Exception as error:  # noqa: BLE001 - se informa tal cual, sin mostrar la clave
        print(f"No se pudo conectar: {type(error).__name__}: {str(error).splitlines()[0][:200]}")
        return 2
    esperado = columnas_esperadas()
    faltan_tablas, faltan_columnas, sobran = comparar(esperado, real)
    print(f"Tablas en pos: {len(real)} (esperadas por las migraciones: {len(esperado)})\n")
    print(f"{'tabla':<26}{'filas':>8}")
    for tabla in sorted(real):
        print(f"{tabla:<26}{filas[tabla]:>8}")
    print()
    for titulo, items in (
        ("FALTAN tablas (aplicar migraciones)", faltan_tablas),
        ("FALTAN columnas (aplicar migraciones, p. ej. la 007)", faltan_columnas),
        ("Sobran tablas (no vienen de las migraciones)", sobran),
    ):
        print(f"{titulo}: {', '.join(items) if items else 'ninguna'}")
    return 1 if (faltan_tablas or faltan_columnas) else 0


if __name__ == "__main__":
    sys.exit(main())
