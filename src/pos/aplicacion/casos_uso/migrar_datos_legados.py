"""Caso de uso: cargar en el sistema nuevo los productos y clientes del sistema antiguo.

Lee los CSV que prepara QA a partir del respaldo (separador «;», UTF-8 con BOM). Reglas (QA 18-11):

- Productos: se crean con su categoria, costo (neto, IVA e impuesto adicional) y existencia
  inicial, que queda en el historial como movimiento «Carga inicial».
- Clientes: se crean con su cupo y su deuda actual como un consumo «Saldo anterior».
- Idempotente: un producto cuyo codigo ya existe, o un cliente cuyo nombre ya existe, se omite
  (no se duplica ni se le cambia el stock o el saldo). Se puede ejecutar dos veces sin riesgo.
- Una fila invalida no frena a las demas: se rechaza con su motivo y queda en el resumen.

Este caso de uso no confirma la transaccion (no hace commit): lo hace quien lo llama. Asi un
simulacro («--simulacro») puede probar todo y deshacerlo.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioCategorias,
    RepositorioClientes,
    RepositorioExistencias,
    RepositorioProductos,
)
from pos.aplicacion.registro_movimientos import RegistroMovimientos
from pos.aplicacion.sincronizacion import (
    encolar_categoria,
    encolar_cliente,
    encolar_existencia,
    encolar_movimiento_cliente,
    encolar_producto,
)
from pos.dominio.clientes import (
    DETALLE_SALDO_ANTERIOR,
    Cliente,
    MovimientoCliente,
    TipoMovimientoCliente,
)
from pos.dominio.errores import ErrorDominio
from pos.dominio.inventario import Existencia, TipoMovimiento
from pos.dominio.productos import Producto, UnidadVenta
from pos.dominio.value_objects import Costo, Dinero

MOTIVO_CARGA_INICIAL = "Carga inicial"
CONTACTO_PENDIENTE = "Sin teléfono (migración)"


class ErrorArchivo(ErrorDominio):
    """El CSV no es el esperado (faltan columnas o no existe)."""


@dataclass(frozen=True)
class Rechazo:
    fila: int  # numero de linea en el archivo (la cabecera es la 1)
    referencia: str  # codigo del producto o numero de cliente (sin datos personales)
    motivo: str


@dataclass
class ResumenMigracion:
    entidad: str  # «productos» o «clientes»
    leidos: int = 0
    cargados: int = 0
    omitidos: int = 0  # ya existian
    rechazados: list[Rechazo] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def lineas(self) -> list[str]:
        out = [
            f"{self.entidad.capitalize()}: {self.leidos} leídos, {self.cargados} cargados, "
            f"{self.omitidos} ya existían, {len(self.rechazados)} rechazados."
        ]
        out += [
            f"  Rechazado (línea {r.fila}, {r.referencia}): {r.motivo}" for r in self.rechazados
        ]
        out += [f"  Aviso: {a}" for a in self.avisos]
        return out


def leer_csv(ruta: Path, columnas: tuple[str, ...]) -> list[dict[str, str]]:
    """Lee un CSV de migracion y comprueba que traiga las columnas que se necesitan."""
    try:
        with ruta.open(encoding="utf-8-sig", newline="") as f:
            lector = csv.DictReader(f, delimiter=";")
            faltan = [c for c in columnas if c not in (lector.fieldnames or [])]
            if faltan:
                raise ErrorArchivo(f"{ruta.name}: faltan las columnas {', '.join(faltan)}")
            return [{k: (v or "").strip() for k, v in fila.items() if k} for fila in lector]
    except OSError as exc:
        raise ErrorArchivo(f"No se pudo leer {ruta}: {exc}") from exc


COLUMNAS_PRODUCTOS = (
    "codigo",
    "nombre",
    "unidad_venta",
    "categoria",
    "precio_venta_con_iva",
    "costo_neto",
    "iva",
    "impuesto_adicional",
    "existencia",
    "stock_minimo",
)
COLUMNAS_CLIENTES = ("nombre", "telefono", "observaciones", "cupo", "deuda_actual", "ultimo_pago")


_FORMATO_ENTERO = re.compile(r"^\d+$|^\d{1,3}(\.\d{3})+$")


def _entero(texto: str, campo: str, minimo: int = 0) -> int | None:
    """Entero de CLP/unidades; vacio = None. Acepta «1234» y «1.234» (separador de miles).

    Un decimal («1500.50», «12,5») es ambiguo: se RECHAZA en vez de adivinar y dejar un monto
    multiplicado por 10 o por 100.
    """
    if not texto:
        return None
    if not _FORMATO_ENTERO.match(texto):
        raise ErrorDominio(
            f"{campo}: «{texto}» no es un número entero (los decimales no se aceptan aquí)"
        )
    valor = int(texto.replace(".", ""))
    if valor < minimo:
        raise ErrorDominio(f"{campo}: no puede ser menor que {minimo}")
    return valor


def _cantidad(texto: str) -> Decimal:
    """Existencia: entero (unidad) o decimal con coma o punto (granel, en kg)."""
    if not texto:
        return Decimal(0)
    try:
        valor = Decimal(texto.replace(",", "."))
    except InvalidOperation as exc:
        raise ErrorDominio(f"existencia: «{texto}» no es un número") from exc
    # Las negativas del sistema antiguo ya vienen en 0; si llegara una, no se arrastra.
    return max(valor, Decimal(0))


@dataclass
class MigrarProductos:
    repositorio: RepositorioProductos
    repositorio_categorias: RepositorioCategorias
    repositorio_existencias: RepositorioExistencias
    movimientos: RegistroMovimientos | None = None
    cola: ColaSincronizacion | None = None
    auditor: Auditor | None = None
    _con_adicional: int = field(default=0, init=False, repr=False)
    _nombre_del_codigo: int = field(default=0, init=False, repr=False)

    def ejecutar(self, filas: list[dict[str, str]]) -> ResumenMigracion:
        resumen = ResumenMigracion("productos", leidos=len(filas))
        self._con_adicional = 0
        self._nombre_del_codigo = 0
        for numero, fila in enumerate(filas, start=2):
            codigo = fila.get("codigo", "")
            try:
                if self._cargar(fila):
                    resumen.cargados += 1
                else:
                    resumen.omitidos += 1
            except ErrorDominio as exc:
                resumen.rechazados.append(Rechazo(numero, codigo or "(sin código)", str(exc)))
        if self._nombre_del_codigo:
            resumen.avisos.append(
                f"{self._nombre_del_codigo} productos no traían nombre pero su código es un "
                "texto: se usó el código como nombre (revisar desde F2)."
            )
        if self._con_adicional:
            resumen.avisos.append(
                f"{self._con_adicional} productos traen impuesto adicional (IABA): su costo neto "
                "ya lo incluye de forma aproximada (definición de la PO, CA-21), así que no se "
                "separa; se ajusta después desde F2 si hace falta."
            )
        if self.auditor is not None and resumen.cargados:
            self.auditor.registrar(
                "Migración de productos",
                "Sistema antiguo",
                "—",
                f"{resumen.cargados} productos cargados",
            )
        return resumen

    def _cargar(self, fila: dict[str, str]) -> bool:
        """True si lo creo; False si ya existia. Lanza ErrorDominio si la fila no sirve."""
        codigo = fila["codigo"].strip()
        if not codigo:
            raise ErrorDominio("falta el código")
        if self.repositorio.obtener_por_codigo(codigo) is not None:
            return False
        unidad = fila["unidad_venta"].lower()
        if unidad not in ("unidad", "granel"):
            raise ErrorDominio(f"unidad de venta «{fila['unidad_venta']}» no reconocida")
        precio = _entero(fila["precio_venta_con_iva"], "precio") or 0
        neto = _entero(fila["costo_neto"], "costo neto")
        costo = None
        if neto is not None:
            costo = Costo(
                Dinero(neto),
                Dinero(_entero(fila["iva"], "IVA") or 0),
                Dinero(_entero(fila["impuesto_adicional"], "impuesto adicional") or 0),
            )
        nombre = fila["nombre"].strip()
        if not nombre and any(c.isalpha() for c in codigo):
            # En el sistema antiguo algunas fichas guardaban la descripcion en el codigo.
            nombre = codigo
            self._nombre_del_codigo += 1
        cantidad = _cantidad(fila["existencia"])
        if costo is not None and costo.impuesto_adicional.monto > 0:
            self._con_adicional += 1
        nombre_categoria = fila["categoria"] or "Sin categoría"
        # Se valida todo lo de la fila antes de guardar el producto y su stock; lo unico que
        # puede quedar de una fila rechazada es la categoria, que ya es una de las validas.
        categoria, creada = self.repositorio_categorias.agregar(nombre_categoria)
        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            precio=Dinero(precio),
            unidad_venta=UnidadVenta(unidad),
            categoria_id=categoria.id,
            costo=costo,
            stock_minimo=_entero(fila["stock_minimo"], "stock mínimo"),
        )
        if creada:
            encolar_categoria(self.cola, categoria.nombre)
        self.repositorio.guardar(producto)
        encolar_producto(self.cola, producto, categoria.nombre)
        existencia = Existencia(codigo, cantidad)
        self.repositorio_existencias.guardar(existencia)
        encolar_existencia(self.cola, existencia)
        if cantidad > 0 and self.movimientos is not None:
            self.movimientos.registrar(
                codigo, TipoMovimiento.ENTRADA, cantidad, MOTIVO_CARGA_INICIAL
            )
        return True


@dataclass
class MigrarClientes:
    repositorio: RepositorioClientes
    fecha_saldo: Callable[[], date]  # dia al que se fecha el «Saldo anterior»
    cola: ColaSincronizacion | None = None
    auditor: Auditor | None = None
    contacto_pendiente: str = CONTACTO_PENDIENTE

    def ejecutar(self, filas: list[dict[str, str]]) -> ResumenMigracion:
        resumen = ResumenMigracion("clientes", leidos=len(filas))
        sin_contacto = 0
        vistos: set[str] = set()
        for numero, fila in enumerate(filas, start=2):
            referencia = f"cliente nº {numero - 1}"  # sin el nombre: es un dato personal
            clave = " ".join(fila["nombre"].split()).casefold()
            if clave and clave in vistos:
                # Dos clientes con el mismo nombre en el archivo: no se puede saber si son la misma
                # persona. Se rechaza el segundo CON su motivo para revisarlo a mano; callarlo
                # perderia su deuda.
                resumen.rechazados.append(
                    Rechazo(numero, referencia, "nombre repetido en el archivo: revisar a mano")
                )
                continue
            vistos.add(clave)
            try:
                estado = self._cargar(fila)
            except ErrorDominio as exc:
                resumen.rechazados.append(Rechazo(numero, referencia, str(exc)))
                continue
            if estado == "omitido":
                resumen.omitidos += 1
                continue
            resumen.cargados += 1
            sin_contacto += estado == "sin_contacto"
        if sin_contacto:
            resumen.avisos.append(
                f"{sin_contacto} clientes no traían teléfono ni correo y quedaron con «"
                f"{self.contacto_pendiente}»: hay que completarlo desde F4."
            )
        if self.auditor is not None and resumen.cargados:
            self.auditor.registrar(
                "Migración de clientes",
                "Sistema antiguo",
                "—",
                f"{resumen.cargados} clientes cargados",
            )
        return resumen

    def _cargar(self, fila: dict[str, str]) -> str:
        """Devuelve «omitido», «sin_contacto» o «ok»."""
        nombre = " ".join(fila["nombre"].split())
        if not nombre:
            raise ErrorDominio("falta el nombre")
        clave = nombre.casefold()
        if any(" ".join(c.nombre.split()).casefold() == clave for c in self.repositorio.listar()):
            return "omitido"
        cupo = _entero(fila["cupo"], "cupo")
        deuda = _entero(fila["deuda_actual"], "deuda") or 0
        telefono = fila["telefono"]
        sin_contacto = not telefono
        cliente = Cliente(
            nombre,
            telefono or self.contacto_pendiente,
            observaciones=fila["observaciones"],
            cupo=cupo,
        )
        self.repositorio.guardar(cliente)
        encolar_cliente(self.cola, cliente)
        if deuda > 0:
            detalle = DETALLE_SALDO_ANTERIOR
            if fila["ultimo_pago"]:
                detalle += f" (último pago {fila['ultimo_pago']})"
            movimiento = MovimientoCliente(
                cliente_id=cliente.id or 0,
                tipo=TipoMovimientoCliente.CONSUMO,
                monto=deuda,
                fecha=self.fecha_saldo(),
                detalle=detalle,
            )
            self.repositorio.agregar_movimiento(movimiento)
            encolar_movimiento_cliente(self.cola, cliente, movimiento)
        return "sin_contacto" if sin_contacto else "ok"
