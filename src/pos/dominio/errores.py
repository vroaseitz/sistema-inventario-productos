"""Excepciones del dominio.

Se separan de las excepciones de infraestructura para que las capas superiores
puedan distinguir un error de reglas de negocio de un fallo tecnico.
"""


class ErrorDominio(Exception):
    """Base de todos los errores de reglas de negocio."""


class CodigoBarrasInvalido(ErrorDominio):
    """El codigo de barras no cumple el formato o el digito verificador."""


class ReglaInventarioInvalida(ErrorDominio):
    """Operacion de inventario que viola una regla (p. ej. stock negativo)."""


class DatosProductoInvalidos(ErrorDominio):
    """Los datos para construir un producto no son validos."""
