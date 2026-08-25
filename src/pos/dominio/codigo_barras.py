"""Analizador de codigos de barras EAN-13, con soporte de peso/precio embebido.

Contexto de negocio
-------------------
Emporio NaturalSur vende productos por unidad y a granel. Las balanzas de tienda
imprimen etiquetas EAN-13 "internas" (GS1 restricted distribution) que empiezan con
prefijo 20-29 y llevan embebido el peso o el precio del producto pesado. Estos codigos
NO son globales: solo tienen sentido dentro de la tienda.

Formato soportado (configurable, con un valor por defecto habitual en Chile)
---------------------------------------------------------------------------
13 digitos:  P I C C C C C V V V V V D

- P (pos 0)      : primer digito. 2 => codigo interno de tienda.
- I (pos 1)      : indicador. Junto con P forma el prefijo 20-29.
- C (pos 2-6)    : codigo interno del producto (5 digitos).
- V (pos 7-11)   : valor embebido (5 digitos): peso en gramos o precio, segun el modo.
- D (pos 12)     : digito verificador EAN-13.

El modo (peso vs precio) y los decimales del valor se parametrizan porque cada balanza
puede configurarse distinto; el valor por defecto asume peso en gramos.

Referencia del digito verificador: estandar EAN-13/GTIN-13.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .errores import CodigoBarrasInvalido

LONGITUD_EAN13 = 13
PREFIJOS_INTERNOS = range(20, 30)  # 20..29


class TipoValorEmbebido(Enum):
    """Que representa el bloque de 5 digitos del valor embebido."""

    PESO_GRAMOS = "peso_gramos"
    PRECIO = "precio"


def _solo_digitos(codigo: str) -> str:
    limpio = codigo.strip()
    if not limpio.isdigit():
        raise CodigoBarrasInvalido(f"El codigo debe ser numerico: {codigo!r}")
    return limpio


def calcular_digito_verificador(doce_digitos: str) -> int:
    """Calcula el 13.o digito EAN-13 a partir de los primeros 12.

    Pesos alternados 1,3,1,3... desde la izquierda; el verificador completa
    la suma al siguiente multiplo de 10.
    """
    d = _solo_digitos(doce_digitos)
    if len(d) != 12:
        raise CodigoBarrasInvalido("Se requieren exactamente 12 digitos para el calculo")
    suma = sum(int(n) * (1 if i % 2 == 0 else 3) for i, n in enumerate(d))
    return (10 - (suma % 10)) % 10


def es_ean13_valido(codigo: str) -> bool:
    """True si `codigo` es un EAN-13 con digito verificador correcto."""
    try:
        d = _solo_digitos(codigo)
    except CodigoBarrasInvalido:
        return False
    if len(d) != LONGITUD_EAN13:
        return False
    return calcular_digito_verificador(d[:12]) == int(d[12])


def es_codigo_interno(codigo: str) -> bool:
    """True si el prefijo (2 primeros digitos) esta en el rango interno 20-29."""
    d = codigo.strip()
    if len(d) < 2 or not d[:2].isdigit():
        return False
    return int(d[:2]) in PREFIJOS_INTERNOS


@dataclass(frozen=True)
class LecturaCodigoBarras:
    """Resultado de analizar un codigo de barras escaneado."""

    codigo: str
    es_interno: bool
    codigo_producto: str
    peso_kg: Decimal | None = None
    precio: Decimal | None = None

    @property
    def es_granel(self) -> bool:
        return self.peso_kg is not None or self.precio is not None


def analizar_codigo(
    codigo: str,
    *,
    tipo_valor: TipoValorEmbebido = TipoValorEmbebido.PESO_GRAMOS,
) -> LecturaCodigoBarras:
    """Analiza un EAN-13 y extrae la informacion segun sea normal o interno con valor.

    - Codigo normal (prefijo != 20-29): devuelve el codigo completo como codigo_producto.
    - Codigo interno (prefijo 20-29): extrae codigo de producto (5 digitos) y el peso/precio.

    Lanza CodigoBarrasInvalido si el formato o el digito verificador no cuadran.
    """
    d = _solo_digitos(codigo)
    if len(d) != LONGITUD_EAN13:
        raise CodigoBarrasInvalido(f"Un EAN-13 tiene {LONGITUD_EAN13} digitos, llegaron {len(d)}")
    if not es_ean13_valido(d):
        raise CodigoBarrasInvalido(f"Digito verificador EAN-13 invalido: {d}")

    if not es_codigo_interno(d):
        return LecturaCodigoBarras(codigo=d, es_interno=False, codigo_producto=d)

    codigo_producto = d[2:7]
    crudo = int(d[7:12])
    if tipo_valor is TipoValorEmbebido.PESO_GRAMOS:
        peso_kg = (Decimal(crudo) / Decimal(1000)).quantize(Decimal("0.001"))
        return LecturaCodigoBarras(
            codigo=d, es_interno=True, codigo_producto=codigo_producto, peso_kg=peso_kg
        )
    precio = Decimal(crudo)
    return LecturaCodigoBarras(
        codigo=d, es_interno=True, codigo_producto=codigo_producto, precio=precio
    )
