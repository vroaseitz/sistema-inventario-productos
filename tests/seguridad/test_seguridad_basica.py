"""Seguridad basica: credenciales fuera del repo, inyeccion SQL y claves hasheadas."""

import subprocess
from pathlib import Path

from pos.dominio.productos import Producto
from pos.dominio.value_objects import Dinero
from pos.infraestructura.sqlite.conexion import crear_conexion
from pos.infraestructura.sqlite.esquema import crear_esquema
from pos.infraestructura.sqlite.repositorio_productos import RepositorioProductosSQLite

RAIZ = Path(__file__).resolve().parents[2]


def test_el_archivo_env_no_esta_versionado():
    archivos = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    versionados = [f for f in archivos if Path(f).name == ".env"]
    assert versionados == []


def test_el_codigo_no_tiene_urls_de_base_con_clave_incrustada():
    for ruta in (RAIZ / "src").rglob("*.py"):
        texto = ruta.read_text(encoding="utf-8")
        assert "postgresql://" not in texto or "@" not in texto.split("postgresql://")[1][:80], ruta


def test_buscar_resiste_inyeccion_sql():
    con = crear_conexion(":memory:")
    crear_esquema(con)
    repo = RepositorioProductosSQLite(con)
    repo.guardar(Producto("A1", "Arroz", Dinero(1000), categoria_id=1))
    for ataque in ("'; DROP TABLE productos; --", "' OR '1'='1", "%", "_"):
        assert repo.buscar(ataque) == [] or ataque in ("%", "_")
    assert [p.codigo for p in repo.listar()] == ["A1"]  # la tabla sigue ahi


def test_las_claves_de_usuarios_no_quedan_en_claro():
    from pos.infraestructura.seguridad.hasheador_bcrypt import HasheadorBcrypt

    hasheador = HasheadorBcrypt(rondas=4)
    hash_ = hasheador.hashear("mi-clave-secreta")
    assert "mi-clave-secreta" not in hash_
    assert hasheador.hashear("mi-clave-secreta") != hash_  # sal distinta en cada hash
    assert hasheador.verificar("mi-clave-secreta", hash_)
    assert not hasheador.verificar("otra", hash_)


def test_dinero_no_usa_float_para_los_montos():
    assert isinstance(Dinero(1990).monto, int)
