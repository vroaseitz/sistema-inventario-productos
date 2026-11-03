"""Proveedores: crear uno nuevo y listar los conocidos (HU-CMP-03).

Un proveedor es conocido si se creo a mano o si ya aparece en alguna factura registrada. Crear uno
con un nombre que ya existe (sin distinguir mayusculas ni tildes) se rechaza: asi no se parten las
compras de un mismo proveedor en dos nombres casi iguales.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.puertos import RepositorioFacturasCompra, RepositorioProveedores
from pos.dominio.compras import Proveedor
from pos.dominio.errores import ReglaCompraInvalida

LARGO_MAXIMO = 80


def _plano(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.lower().split())


@dataclass
class GestionarProveedores:
    repositorio: RepositorioProveedores
    repositorio_facturas: RepositorioFacturasCompra | None = None
    auditor: Auditor | None = None

    def nombres(self) -> list[str]:
        """Todos los proveedores conocidos, sin repetir y ordenados."""
        vistos: dict[str, str] = {}
        for p in self.repositorio.listar():
            vistos.setdefault(_plano(p.nombre), p.nombre)
        if self.repositorio_facturas is not None:
            for nombre in self.repositorio_facturas.proveedores():
                vistos.setdefault(_plano(nombre), nombre)
        return sorted(vistos.values(), key=_plano)

    def crear(self, nombre: str, contacto: str = "") -> Proveedor:
        nombre = " ".join(nombre.split())
        contacto = contacto.strip()
        if not nombre:
            raise ReglaCompraInvalida("Falta el nombre del proveedor")
        if len(nombre) > LARGO_MAXIMO:
            raise ReglaCompraInvalida(f"El nombre no puede pasar de {LARGO_MAXIMO} caracteres")
        for existente in self.nombres():
            if _plano(existente) == _plano(nombre):
                raise ReglaCompraInvalida(f"Ya existe el proveedor «{existente}»")
        self.repositorio.agregar(nombre, contacto)
        if self.auditor is not None:
            self.auditor.registrar("Nuevo proveedor", nombre, "—", "creado")
        return Proveedor(nombre, contacto)
