"""Formato y lectura de montos en pesos chilenos (O-07, O-27).

Funcion unica para toda la aplicacion: pantallas y mensajes de error usan punto de miles.
"""


def formatear_clp(monto: int) -> str:
    """26074 -> '$26.074' (el signo menos va antes del $)."""
    signo = "-" if monto < 0 else ""
    return f"{signo}${abs(monto):,}".replace(",", ".")


def parsear_monto(texto: str) -> int:
    """Acepta '5.000', '5000' y '$5.000'; levanta ValueError si no es un entero."""
    limpio = texto.strip().lstrip("$").replace(".", "").replace(" ", "")
    return int(limpio)
