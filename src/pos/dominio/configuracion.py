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
        "Para productos sin «Días aviso» propio (HU-INV-03). El prototipo propone 14: "
        "pendiente de confirmar con la Product Owner.",
    ),
    Parametro(
        "abrir_cajon",
        "Abrir el cajon al cobrar en efectivo",
        1,
        0,
        1,
        "1 = si, 0 = no",
        "El cajon va conectado a la impresora y se abre con una venta en efectivo (HU-VTA-06).",
    ),
    Parametro(
        "meta_lunes_viernes",
        "Meta de ganancia: lunes a viernes",
        0,
        0,
        100_000_000,
        "CLP",
        "Ganancia diaria que se espera. 0 = sin meta cargada (HU-REP-05).",
    ),
    Parametro(
        "meta_sabado",
        "Meta de ganancia: sábado",
        0,
        0,
        100_000_000,
        "CLP",
        "0 = sin meta cargada. Los valores reales salen del Excel de punto de equilibrio.",
    ),
    Parametro(
        "meta_domingo",
        "Meta de ganancia: domingo y festivos",
        0,
        0,
        100_000_000,
        "CLP",
        "0 = sin meta cargada. Hoy los festivos no se distinguen: rige el domingo.",
    ),
    Parametro(
        "inactividad_minutos",
        "Cierre de sesión por inactividad",
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
        raise ErrorDominio(f"{parametro.titulo}: escribe un número entero") from exc
    if not parametro.minimo <= valor <= parametro.maximo:
        raise ErrorDominio(
            f"{parametro.titulo}: debe estar entre {parametro.minimo} y {parametro.maximo} "
            f"{parametro.unidad}"
        )
    return valor
