"""Proveedores (HU-CMP-03): crear, no duplicar y mezclar los creados con los de las facturas."""

from datetime import date

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.gestionar_proveedores import GestionarProveedores
from pos.dominio.compras import FacturaCompra
from pos.dominio.errores import ReglaCompraInvalida
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
from pos.infraestructura.sqlite.repositorio_facturas_compra import (
    RepositorioFacturasCompraSQLite,
)
from pos.infraestructura.sqlite.repositorio_proveedores import RepositorioProveedoresSQLite


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        proveedores = RepositorioProveedoresSQLite(con)
        facturas = RepositorioFacturasCompraSQLite(con)
        auditoria = RepositorioAuditoriaSQLite(con)

    a = A()
    a.gestion = GestionarProveedores(
        a.proveedores, a.facturas, Auditor(a.auditoria, lambda: "roxana")
    )
    return a


def test_crear_proveedor_lo_deja_en_la_lista_con_su_contacto(app):
    app.gestion.crear("  Distribuidora   Sur ", " +56 9 1111 1111 ")
    (proveedor,) = app.proveedores.listar()
    assert (proveedor.nombre, proveedor.contacto) == ("Distribuidora Sur", "+56 9 1111 1111")
    assert app.gestion.nombres() == ["Distribuidora Sur"]


def test_no_se_repite_un_proveedor_aunque_cambien_mayusculas_o_tildes(app):
    app.gestion.crear("Distribuidora Sur")
    for variante in ("distribuidora sur", "DISTRIBUIDÓRA  SUR"):
        with pytest.raises(ReglaCompraInvalida, match="Ya existe el proveedor «Distribuidora Sur»"):
            app.gestion.crear(variante)
    assert len(app.proveedores.listar()) == 1


def test_nombre_vacio_o_demasiado_largo_se_rechaza(app):
    with pytest.raises(ReglaCompraInvalida, match="Falta el nombre"):
        app.gestion.crear("   ")
    with pytest.raises(ReglaCompraInvalida, match="no puede pasar"):
        app.gestion.crear("x" * 81)


def test_los_proveedores_de_las_facturas_tambien_cuentan_y_no_se_duplican(app):
    app.facturas.guardar(FacturaCompra("Frutos del Valle", "F-1", date(2026, 11, 2), 1000, 190))
    app.gestion.crear("Distribuidora Sur")
    assert app.gestion.nombres() == ["Distribuidora Sur", "Frutos del Valle"]
    with pytest.raises(ReglaCompraInvalida, match="Ya existe"):
        app.gestion.crear("frutos del valle")  # ya sale en una factura


def test_crear_un_proveedor_queda_en_la_auditoria(app):
    app.gestion.crear("Distribuidora Sur")
    assert [f["accion"] for f in app.auditoria.listar()] == ["Nuevo proveedor"]
