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


def _con_factura(app, proveedor="Distribuidora Sur", numero="F-1"):
    from pos.dominio.compras import LineaFactura

    linea = LineaFactura("ARR", 2, 1000)
    app.facturas.guardar(FacturaCompra(proveedor, numero, date(2026, 11, 1), 2000, 380, [linea]))


def test_editar_un_proveedor_cambia_nombre_y_contacto_y_sus_facturas_lo_siguen(app):
    """CO-02: renombrar no deja las facturas ya registradas con un nombre que ya no existe."""
    app.gestion.crear("Distribuidora Sur", "viejo@sur.cl")
    _con_factura(app)
    nuevo = app.gestion.modificar("Distribuidora Sur", "  Distribuidora   Sur SpA ", "nuevo@sur.cl")
    assert (nuevo.nombre, nuevo.contacto) == ("Distribuidora Sur SpA", "nuevo@sur.cl")
    (proveedor,) = app.proveedores.listar()
    assert (proveedor.nombre, proveedor.contacto) == ("Distribuidora Sur SpA", "nuevo@sur.cl")
    assert [f.proveedor for f in app.facturas.listar()] == ["Distribuidora Sur SpA"]
    assert app.gestion.nombres() == ["Distribuidora Sur SpA"]  # sin el nombre viejo repetido
    registro = next(f for f in app.auditoria.listar() if f["accion"] == "Edición de proveedor")
    assert "viejo@sur.cl" in registro["antes"] and "nuevo@sur.cl" in registro["despues"]


def test_editar_un_proveedor_no_puede_quedar_con_el_nombre_de_otro(app):
    app.gestion.crear("Distribuidora Sur")
    app.gestion.crear("Frutos del Valle")
    with pytest.raises(ReglaCompraInvalida, match="Ya existe"):
        app.gestion.modificar("Frutos del Valle", "distribuidora sur")
    with pytest.raises(ReglaCompraInvalida, match="nombre"):
        app.gestion.modificar("Frutos del Valle", "   ")
    assert app.gestion.nombres() == ["Distribuidora Sur", "Frutos del Valle"]


def test_editar_solo_el_contacto_o_cambiar_una_mayuscula_es_valido(app):
    app.gestion.crear("distribuidora sur", "a@sur.cl")
    app.gestion.modificar("distribuidora sur", "Distribuidora Sur", "a@sur.cl")  # solo mayuscula
    assert [p.nombre for p in app.proveedores.listar()] == ["Distribuidora Sur"]
    app.gestion.modificar("Distribuidora Sur", "Distribuidora Sur", "b@sur.cl")  # solo contacto
    assert app.proveedores.listar()[0].contacto == "b@sur.cl"


def test_un_proveedor_que_solo_existe_por_sus_facturas_tambien_se_puede_editar(app):
    _con_factura(app, "Solo Factura")
    app.gestion.modificar("Solo Factura", "Solo Factura Ltda", "x@sf.cl")
    assert [p.nombre for p in app.proveedores.listar()] == ["Solo Factura Ltda"]
    assert [f.proveedor for f in app.facturas.listar()] == ["Solo Factura Ltda"]


def test_sin_cambios_no_se_registra_nada_en_la_auditoria(app):
    app.gestion.crear("Distribuidora Sur", "a@sur.cl")
    antes = len(app.auditoria.listar())
    app.gestion.modificar("Distribuidora Sur", "Distribuidora Sur", "a@sur.cl")
    assert len(app.auditoria.listar()) == antes


def test_editar_un_proveedor_encola_el_renombrado_para_supabase(app):
    from pos.infraestructura.sqlite.cola_sincronizacion import ColaSincronizacionSQLite
    from pos.infraestructura.supabase.traductor import traducir_operacion

    cola = ColaSincronizacionSQLite(app.proveedores._con)
    gestion = GestionarProveedores(app.proveedores, app.facturas, cola=cola)
    gestion.crear("Distribuidora Sur")
    gestion.modificar("Distribuidora Sur", "Distribuidora Sur SpA", "n@sur.cl")
    (op,) = [p for p in cola.pendientes() if p["entidad"] == "proveedor_renombrar"]
    assert op["datos"] == {
        "anterior": "Distribuidora Sur",
        "nuevo": "Distribuidora Sur SpA",
        "contacto": "n@sur.cl",
    }
    renombrar, asegurar = traducir_operacion(op)
    assert renombrar[0].startswith("UPDATE pos.proveedor SET nombre = %s, contacto = %s")
    assert renombrar[1] == (
        "Distribuidora Sur SpA",
        "n@sur.cl",
        "Distribuidora Sur",
        "Distribuidora Sur SpA",
        "Distribuidora Sur",
    )
    assert "INSERT INTO pos.proveedor" in asegurar[0]  # si el anterior nunca llego, entra igual
