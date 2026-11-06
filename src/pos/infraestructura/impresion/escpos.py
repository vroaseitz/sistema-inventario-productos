"""Bytes ESC/POS para impresoras termicas de 58 mm (Xprinter y compatibles)."""

from __future__ import annotations

INICIAR = b"\x1b@"
CORTE_PARCIAL = b"\x1dV\x42\x00"
# ESC p m t1 t2: pulso al cajon conectado al conector de la impresora (pin 2).
PULSO_CAJON = b"\x1bp\x00\x19\xfa"
CODIFICACION = "cp858"  # tildes y enie en la tabla de caracteres 19 (PC858) de las Xprinter
SELECCIONAR_CP858 = b"\x1bt\x13"


def a_escpos(lineas: list[str], abrir_cajon: bool = False, cortar: bool = True) -> bytes:
    """Texto + avance de papel + corte, y opcionalmente el pulso que abre el cajon."""
    datos = INICIAR + SELECCIONAR_CP858
    for linea in lineas:
        datos += linea.encode(CODIFICACION, errors="replace") + b"\n"
    datos += b"\n\n\n"
    if cortar:
        datos += CORTE_PARCIAL
    if abrir_cajon:
        datos += PULSO_CAJON
    return datos
