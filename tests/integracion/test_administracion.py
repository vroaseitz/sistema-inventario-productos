"""F7 Administracion: usuarios y perfiles, auditoria, configuracion y permisos (SQLite real)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.casos_uso.autenticar_usuario import AutenticarUsuario
from pos.aplicacion.casos_uso.consultar_alertas_vencimiento import ConsultarAlertasVencimiento
from pos.aplicacion.casos_uso.editar_producto import EditarProducto
from pos.aplicacion.casos_uso.gestionar_usuarios import GestionarUsuarios
from pos.aplicacion.casos_uso.ingresar_stock import IngresarStock
from pos.aplicacion.casos_uso.registrar_merma import RegistrarMerma
from pos.aplicacion.casos_uso.registrar_producto import RegistrarProducto
from pos.dominio.configuracion import validar_parametro
from pos.dominio.errores import ErrorDominio
from pos.dominio.inventario import MotivoAjuste
from pos.dominio.productos import Producto
from pos.dominio.usuarios import (
    CredencialesInvalidas,
    Rol,
    modulos_permitidos,
)
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_auditoria import RepositorioAuditoriaSQLite
from pos.infraestructura.sqlite.repositorio_configuracion import RepositorioConfiguracionSQLite
from pos.infraestructura.sqlite.repositorio_existencias import (
    RepositorioAjustesSQLite,
    RepositorioExistenciasSQLite,
)
from pos.infraestructura.sqlite.repositorio_historial import RepositorioHistorialSQLite
from pos.infraestructura.sqlite.repositorio_lotes import RepositorioLotesSQLite
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite
from pos.infraestructura.sqlite.repositorio_usuarios import RepositorioUsuariosSQLite


class HasheadorFalso:
    def hashear(self, clave: str) -> str:
        return "hash:" + clave

    def verificar(self, clave: str, clave_hash: str) -> bool:
        return clave_hash == "hash:" + clave


@pytest.fixture
def app():
    con = crear_conexion(":memory:")
    crear_esquema(con)

    class A:
        usuarios = RepositorioUsuariosSQLite(con)
        auditoria = RepositorioAuditoriaSQLite(con)
        config = RepositorioConfiguracionSQLite(con)
        productos = RepositorioProductosSQLite(con)
        existencias = RepositorioExistenciasSQLite(con)
        lotes = RepositorioLotesSQLite(con)
        historial = RepositorioHistorialSQLite(con)
        quien = "roxana"

    a = A()
    a.auditor = Auditor(a.auditoria, lambda: a.quien)
    a.gestion = GestionarUsuarios(a.usuarios, HasheadorFalso(), a.auditor)
    a.gestion.crear("roxana", "clave-segura-1", "clave-segura-1", Rol.ADMIN)
    return a


def test_crear_usuario_valida_claves_y_duplicados(app):
    with pytest.raises(ErrorDominio, match="no coinciden"):
        app.gestion.crear("ana", "clave-segura-1", "otra-clave-12", Rol.CAJERO)
    with pytest.raises(ErrorDominio, match="al menos 8"):
        app.gestion.crear("ana", "corta", "corta", Rol.CAJERO)
    app.gestion.crear("Mostrador", "clave-segura-2", "clave-segura-2", Rol.CAJERO)
    assert app.usuarios.obtener_por_nombre("mostrador").rol is Rol.CAJERO
    with pytest.raises(ErrorDominio, match="Ya existe"):
        app.gestion.crear("MOSTRADOR", "clave-segura-2", "clave-segura-2", Rol.CAJERO)


def test_cambiar_mi_clave_exige_la_actual(app):
    with pytest.raises(CredencialesInvalidas, match="actual no es correcta"):
        app.gestion.cambiar_mi_clave("roxana", "mala", "clave-nueva-123", "clave-nueva-123")
    with pytest.raises(ErrorDominio, match="distinta"):
        app.gestion.cambiar_mi_clave("roxana", "clave-segura-1", "clave-segura-1", "clave-segura-1")
    app.gestion.cambiar_mi_clave("roxana", "clave-segura-1", "clave-nueva-123", "clave-nueva-123")
    entrar = AutenticarUsuario(app.usuarios, HasheadorFalso()).ejecutar
    with pytest.raises(CredencialesInvalidas):
        entrar("roxana", "clave-segura-1")
    assert entrar("roxana", "clave-nueva-123").nombre == "roxana"


def test_siempre_queda_una_administradora_activa(app):
    app.gestion.crear("germaine", "clave-segura-3", "clave-segura-3", Rol.ADMIN)
    app.gestion.cambiar_perfil("germaine", Rol.CAJERO)  # quedan 2 -> 1 admin: permitido
    with pytest.raises(ErrorDominio, match="al menos una administradora"):
        app.gestion.cambiar_perfil("roxana", Rol.CAJERO)
    with pytest.raises(ErrorDominio, match="al menos una administradora"):
        app.gestion.cambiar_estado("roxana", False, quien="germaine")
    with pytest.raises(ErrorDominio, match="tu propio usuario"):
        app.gestion.crear("otra", "clave-segura-4", "clave-segura-4", Rol.ADMIN)
        app.gestion.cambiar_estado("otra", False, quien="otra")


def test_usuario_inactivo_no_entra_y_registra_ultimo_acceso(app):
    app.gestion.crear("ana", "clave-segura-5", "clave-segura-5", Rol.CAJERO)
    entrar = AutenticarUsuario(app.usuarios, HasheadorFalso()).ejecutar
    assert app.usuarios.obtener_por_nombre("ana").ultimo_acceso is None
    entrar("ana", "clave-segura-5")
    assert app.usuarios.obtener_por_nombre("ana").ultimo_acceso is not None
    app.gestion.cambiar_estado("ana", False, quien="roxana")
    with pytest.raises(CredencialesInvalidas):
        entrar("ana", "clave-segura-5")
    app.gestion.cambiar_estado("ana", True)
    assert entrar("ana", "clave-segura-5").activo


def test_cada_cambio_de_usuarios_deja_rastro_con_antes_y_despues(app):
    app.gestion.crear("ana", "clave-segura-5", "clave-segura-5", Rol.CAJERO)
    app.gestion.cambiar_perfil("ana", Rol.ADMIN)
    app.gestion.restablecer_clave("ana", "clave-nueva-777", "clave-nueva-777")
    app.gestion.cambiar_estado("ana", False, quien="roxana")
    filas = {f["accion"]: f for f in app.auditoria.listar()}
    assert filas["Cambio de perfil"]["antes"] == "Vendedora"
    assert filas["Cambio de perfil"]["despues"] == "Administradora"
    assert filas["Desactivación de usuario"]["usuario"] == "roxana"
    assert "Restablecimiento de contraseña" in filas
    assert not any("clave" in str(f["detalle"]) for f in filas.values())  # nunca la clave


def test_auditoria_de_productos_precio_merma_y_filtros(app):
    ingresar = IngresarStock(app.productos, app.existencias, app.lotes)
    RegistrarProducto(app.productos, auditor=app.auditor).ejecutar(
        "CAS", "Castana de caju", 21900, categoria_id=1
    )
    editar = EditarProducto(app.productos, app.historial, auditor=app.auditor)
    editar.ejecutar("CAS", "Castana de caju", 22220, 1, "roxana")
    editar.ejecutar("CAS", "Castana de caju", 22220, 1, "roxana")  # sin cambio de precio: no audita
    ingresar.ejecutar("CAS", Decimal("12"), "Compra")
    app.quien = "germaine"
    RegistrarMerma(
        app.existencias,
        RepositorioAjustesSQLite(app.productos._con),
        app.lotes,
        auditor=app.auditor,
    ).ejecutar("CAS", 3, MotivoAjuste.VENCIMIENTO, "germaine", "retirado de sala")
    filas = app.auditoria.listar()
    acciones = [f["accion"] for f in filas]
    assert acciones.count("Cambio de precio") == 1
    precio = next(f for f in filas if f["accion"] == "Cambio de precio")
    assert (precio["antes"], precio["despues"]) == ("$21.900", "$22.220")
    merma = next(f for f in filas if f["accion"].startswith("Merma"))
    assert (merma["usuario"], merma["antes"], merma["despues"]) == ("germaine", "12", "9")
    assert [f["accion"] for f in app.auditoria.listar(usuario="germaine")] == [merma["accion"]]
    manana = date.today() + timedelta(days=1)
    assert app.auditoria.listar(desde=manana) == []
    assert len(app.auditoria.listar(desde=date.today(), hasta=date.today())) == len(filas)


def test_configuracion_valida_guarda_y_restaura(app):
    assert app.config.obtener("fondo_habitual") == 15000  # defecto
    assert validar_parametro("fondo_habitual", "20.000") == 20000
    with pytest.raises(ErrorDominio, match="numero entero"):
        validar_parametro("fondo_habitual", "mucho")
    with pytest.raises(ErrorDominio, match="entre 1 y 365"):
        validar_parametro("aviso_defecto_dias", "0")
    app.config.guardar("fondo_habitual", 20000)
    assert app.config.obtener("fondo_habitual") == 20000
    app.config.restaurar_valores_por_defecto()
    assert app.config.obtener("fondo_habitual") == 15000


def test_el_aviso_por_defecto_de_la_configuracion_gobierna_las_alertas(app):
    ingresar = IngresarStock(app.productos, app.existencias, app.lotes)
    # Un perecible siempre trae sus propios dias de aviso (C-05a): el aviso por defecto rige para
    # un producto sin perecible que igual se ingreso con fecha de vencimiento.
    app.productos.guardar(Producto("YOG", "Yogurt", Dinero(2000), categoria_id=1))
    ingresar.ejecutar("YOG", 5, "Compra", fecha_vencimiento=date.today() + timedelta(days=10))
    alertas = ConsultarAlertasVencimiento(app.lotes, app.productos, configuracion=app.config)
    assert alertas.ejecutar() == []  # 10 dias > aviso por defecto de 7
    app.config.guardar("aviso_defecto_dias", 14)
    assert [a.nombre_producto for a in alertas.ejecutar()] == ["Yogurt"]


def test_permisos_por_perfil():
    assert modulos_permitidos(Rol.ADMIN) == {"F1", "F2", "F3", "F4", "F5", "F6", "F7"}
    assert modulos_permitidos(Rol.CAJERO) == {"F1"}
    assert "F7" in modulos_permitidos(None)  # sin login (demo y pruebas) se permite todo
