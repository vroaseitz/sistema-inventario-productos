"""Parametros de operacion editables en F7 Configuracion (HU-CAJ-01, HU-INV-03, HU-USR-01)."""

from __future__ import annotations

from dataclasses import dataclass

from .errores import ErrorDominio


@dataclass(frozen=True)
class Parametro:
    clave: str
    titulo: str
    defecto: int
    minimo: int
    maximo: int
    unidad: str
    ayuda: str


PARAMETROS = (
    Parametro(
        "fondo_habitual",
        "Fondo de caja habitual",
        15000,
        0,
        10_000_000,
        "CLP",
        "Con cuanto se abre la caja normalmente (HU-CAJ-01).",
    ),
    Parametro(
        "aviso_defecto_dias",
        "Aviso de vencimiento por defecto",
        7,
        1,
        365,
        "dias",
        "Para productos sin «Dias aviso» propio (HU-INV-03). El prototipo propone 14: "
        "pendiente de confirmar con la Product Owner.",
    ),
    Parametro(
        "inactividad_minutos",
        "Cierre de sesion por inactividad",
        15,
        0,
        600,
        "minutos",
        "Sin tocar el sistema ese tiempo, pide la clave de nuevo. 0 = nunca (HU-USR-01).",
    ),
)
POR_CLAVE = {p.clave: p for p in PARAMETROS}


def validar_parametro(clave: str, texto: str) -> int:
    parametro = POR_CLAVE[clave]
    try:
        valor = int(texto.strip().replace(".", ""))
    except ValueError as exc:
        raise ErrorDominio(f"{parametro.titulo}: escribe un numero entero") from exc
    if not parametro.minimo <= valor <= parametro.maximo:
        raise ErrorDominio(
            f"{parametro.titulo}: debe estar entre {parametro.minimo} y {parametro.maximo} "
            f"{parametro.unidad}"
        )
    return valor
