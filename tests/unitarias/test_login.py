"""Login con bcrypt (HU-USR-01): hash, autenticacion y no revelar que dato fallo."""

import pytest

from pos.aplicacion.casos_uso.autenticar_usuario import AutenticarUsuario, CrearUsuario
from pos.dominio.errores import ErrorDominio
from pos.dominio.usuarios import CredencialesInvalidas, Rol, Usuario
from pos.infraestructura.seguridad.hasheador_bcrypt import HasheadorBcrypt
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_usuarios import RepositorioUsuariosSQLite


@pytest.fixture
def servicios():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    repo = RepositorioUsuariosSQLite(con)
    hasheador = HasheadorBcrypt(rondas=4)  # rapido en pruebas
    return repo, CrearUsuario(repo, hasheador), AutenticarUsuario(repo, hasheador), con


def test_la_clave_se_guarda_hasheada_nunca_en_claro(servicios):
    repo, crear, _, con = servicios
    crear.ejecutar("Ana", "clave-segura-1", Rol.ADMIN)
    guardado = con.execute("SELECT clave_hash FROM usuarios").fetchone()["clave_hash"]
    assert "clave-segura-1" not in guardado and guardado.startswith("$2")


def test_login_correcto_devuelve_el_usuario(servicios):
    _, crear, autenticar, _ = servicios
    crear.ejecutar("Ana", "clave-segura-1", Rol.ADMIN)
    usuario = autenticar.ejecutar(" ANA ", "clave-segura-1")  # el nombre no distingue mayusculas
    assert usuario.nombre == "ana" and usuario.rol is Rol.ADMIN and usuario.id is not None


@pytest.mark.parametrize(
    ("nombre", "clave"), [("ana", "otra-clave-xx"), ("nadie", "clave-segura-1")]
)
def test_login_fallido_da_el_mismo_error(servicios, nombre, clave):
    _, crear, autenticar, _ = servicios
    crear.ejecutar("ana", "clave-segura-1")
    with pytest.raises(CredencialesInvalidas, match="Usuario o clave incorrectos"):
        autenticar.ejecutar(nombre, clave)


def test_usuario_inactivo_no_entra(servicios):
    repo, _, autenticar, _ = servicios
    repo.guardar(Usuario("bob", HasheadorBcrypt(rondas=4).hashear("clave-segura-1"), activo=False))
    with pytest.raises(CredencialesInvalidas):
        autenticar.ejecutar("bob", "clave-segura-1")


def test_clave_corta_y_usuario_duplicado_se_rechazan(servicios):
    _, crear, _, _ = servicios
    with pytest.raises(ErrorDominio):
        crear.ejecutar("ana", "corta")
    crear.ejecutar("ana", "clave-segura-1")
    with pytest.raises(ErrorDominio):
        crear.ejecutar("ANA", "clave-segura-2")


def test_hash_corrupto_no_rompe_la_verificacion():
    assert HasheadorBcrypt().verificar("x", "no-es-un-hash") is False
