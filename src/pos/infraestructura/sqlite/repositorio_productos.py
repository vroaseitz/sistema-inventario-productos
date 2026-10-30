"""Repositorio de productos sobre SQLite. Implementa el puerto RepositorioProductos."""

from __future__ import annotations

import sqlite3

from pos.dominio.categorias import Categoria
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero

_TILDES = "áéíóúüñÁÉÍÓÚÜÑ"
_SIN_TILDES = "aeiouunaeiouun"


def _normalizar_sql(texto: str) -> str:
    """Quita tildes (mayusculas y minusculas) y pasa a minusculas."""
    return texto.translate(str.maketrans(_TILDES, _SIN_TILDES)).lower()


class RepositorioProductosSQLite:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def guardar(self, producto: Producto) -> None:
        """Upsert: inserta o actualiza. Persiste costo, perecible y dias_aviso (C-05b)."""
        # SQL parametrizado (nunca interpolacion de strings): evita inyeccion SQL.
        self._con.execute(
            """
            INSERT INTO productos (
                codigo, nombre, precio, unidad_venta, categoria_id, activo,
                costo_neto, perecible, dias_aviso
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                nombre=excluded.nombre,
                precio=excluded.precio,
                unidad_venta=excluded.unidad_venta,
                categoria_id=excluded.categoria_id,
                activo=excluded.activo,
                costo_neto=excluded.costo_neto,
                perecible=excluded.perecible,
                dias_aviso=excluded.dias_aviso
            """,
            (
                producto.codigo,
                producto.nombre,
                producto.precio.monto,
                producto.unidad_venta.value,
                producto.categoria_id,
                1 if producto.activo else 0,
                producto.costo.neto.monto if producto.costo is not None else None,
                1 if producto.perecible else 0,
                producto.dias_aviso,
            ),
        )

    def obtener_por_codigo(self, codigo: str) -> Producto | None:
        fila = self._con.execute("SELECT * FROM productos WHERE codigo = ?", (codigo,)).fetchone()
        return self._a_producto(fila) if fila else None

    def listar(self) -> list[Producto]:
        filas = self._con.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
        return [self._a_producto(f) for f in filas]

    # --- Catalogo de categorias (C-02/C-04) ---------------------------------

    def listar_categorias(self) -> list[Categoria]:
        """Categorias desde la BD: la lista la define el negocio, no el codigo."""
        filas = self._con.execute("SELECT id, nombre FROM categoria ORDER BY id").fetchall()
        return [Categoria(id=f["id"], nombre=f["nombre"]) for f in filas]

    def crear_categoria(self, nombre: str) -> Categoria:
        """Agrega una categoria nueva. Falla si ya existe (nombre UNIQUE)."""
        nombre = nombre.strip().lower()
        if not nombre:
            raise ValueError("El nombre de categoria no puede estar vacio")
        cursor = self._con.execute("INSERT INTO categoria (nombre) VALUES (?)", (nombre,))
        return Categoria(id=cursor.lastrowid, nombre=nombre)

    @staticmethod
    def _a_producto(fila: sqlite3.Row) -> Producto:
        """Reconstruye la entidad desde la fila, incluidos costo/perecible (C-05b).

        Solo se restaura el neto almacenado: el IVA y el impuesto adicional son
        datos de factura que se capturan tal cual, no se recalculan aqui para no
        inflar el costo al leerlo desde la BD.
        """
        costo = None
        if fila["costo_neto"] is not None:
            costo = Costo(neto=Dinero(int(fila["costo_neto"])), iva=Dinero(0))
        return Producto(
            codigo=fila["codigo"],
            nombre=fila["nombre"],
            precio=Dinero(int(fila["precio"])),
            unidad_venta=UnidadVenta(fila["unidad_venta"]),
            categoria_id=fila["categoria_id"],
            activo=bool(fila["activo"]),
            costo=costo,
            perecible=bool(fila["perecible"]),
            dias_aviso=fila["dias_aviso"],
        )

    def buscar(self, termino: str) -> list[Producto]:
        """Busqueda insensible a mayusculas y tildes.

        SQLite no trae `translate()`, y `LIKE` es case-insensitive solo para
        ASCII: por eso se normaliza (quita tildes + minusculas) el patron en
        Python y tambien la columna, comparando contra una proyeccion
        normalizada. El filtrado ocurre en SQL, sin recorrido en memoria.
        """
        patron = _normalizar_sql(termino.strip())
        if not patron:
            return self.listar()

        query = """
            SELECT * FROM productos
            WHERE activo = 1
            AND (
                LOWER(replace(replace(replace(replace(replace(
                    replace(nombre, 'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'),
                    'ñ','n')) LIKE ?
                OR LOWER(replace(replace(replace(replace(replace(
                    replace(nombre, 'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'),
                    'ñ','n')) LIKE ?
                OR LOWER(replace(replace(replace(replace(replace(
                    replace(codigo, 'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'),
                    'ñ','n')) = ?
            )
            ORDER BY
                -- C-15: los que EMPIEZAN con el termino van primero.
                CASE WHEN LOWER(replace(replace(replace(replace(replace(
                        replace(nombre, 'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'),
                        'ñ','n')) LIKE ? THEN 1 ELSE 2 END,
                nombre
        """

        patron_norm = _normalizar_sql(patron)
        filas = self._con.execute(
            query,
            (
                f"%{patron}%",
                f"{patron_norm}%",
                patron,
                f"{patron_norm}%",
            ),
        ).fetchall()
        return [self._a_producto(fila) for fila in filas]
