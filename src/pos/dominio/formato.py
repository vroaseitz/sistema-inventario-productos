"""Formato y lectura de montos en pesos chilenos (O-07, O-27), y orden de las busquedas.

Funcion unica para toda la aplicacion: pantallas y mensajes de error usan punto de miles.
"""

import unicodedata


def plano(texto: str) -> str:
    """Minusculas y sin tildes: «Té» y «te» son lo mismo al buscar."""
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def rango_de_busqueda(nombre: str, buscado: str) -> int:
    """Orden de una coincidencia (CA-15): 0 el nombre empieza con lo escrito, 1 una palabra
    empieza con ello, 2 solo lo contiene, 3 no coincide. Sin distinguir tildes ni mayusculas."""
    clave, nombre_plano = plano(buscado.strip()), plano(nombre)
    if not clave or nombre_plano.startswith(clave):
        return 0
    if any(palabra.startswith(clave) for palabra in nombre_plano.split()):
        return 1
    return 2 if clave in nombre_plano else 3


def formatear_clp(monto: int) -> str:
    """26074 -> '$26.074' (el signo menos va antes del $)."""
    signo = "-" if monto < 0 else ""
    return f"{signo}${abs(monto):,}".replace(",", ".")


def parsear_monto(texto: str) -> int:
    """Acepta '5.000', '5000' y '$5.000'; levanta ValueError si no es un entero."""
    limpio = texto.strip().lstrip("$").replace(".", "").replace(" ", "")
    return int(limpio)


def formatear_cantidad(valor) -> str:
    """Cantidad sin ceros sobrantes: 30 -> '30', 100 -> '100', 2.500 -> '2,5', 0.350 -> '0,35'.

    Solo se recortan los ceros de los decimales; un entero nunca pierde sus ceros (30 no es 3).
    """
    texto = f"{valor:f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",") or "0"
