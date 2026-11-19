"""Guardas sobre los archivos de migracion (no requieren base de datos)."""

import re
from pathlib import Path

MIGRACIONES = Path(__file__).resolve().parents[2] / "database" / "migraciones"


def _numero(ruta: Path) -> int:
    return int(re.match(r"(\d+)_", ruta.name).group(1))


def test_migraciones_posteriores_a_005_reaplican_permisos_de_pos_app():
    """Una tabla nueva sin GRANT/politica rompe la sincronizacion en silencio (premortem #7)."""
    nuevas = [m for m in sorted(MIGRACIONES.glob("[0-9]*.sql")) if _numero(m) > 5]
    for migracion in nuevas:
        texto = migracion.read_text()
        if re.search(r"CREATE TABLE", texto, re.IGNORECASE):
            assert "aplicar_permisos_pos_app" in texto, (
                f"{migracion.name} crea tablas pero no llama a pos.aplicar_permisos_pos_app()"
            )


def test_migraciones_estan_numeradas_sin_huecos():
    numeros = [_numero(m) for m in sorted(MIGRACIONES.glob("[0-9]*.sql"))]
    assert numeros == list(range(1, len(numeros) + 1))
