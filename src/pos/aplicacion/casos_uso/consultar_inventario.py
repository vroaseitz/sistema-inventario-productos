"""Consultas de F3 Inventario: existencias con stock minimo, inventario valorizado y movimientos.

HU-INV-05 (stock minimo), HU-INV-07 (inventario valorizado) y HU-INV-08 (historial de movimientos).
Los productos a granel se muestran en kilos pero NO se valorizan (decision del levantamiento, igual
que en el prototipo), y un producto sin costo no se valoriza en cero: se lista aparte.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pos.aplicacion.auditor import Auditor
from pos.aplicacion.puertos import (
    ColaSincronizacion,
    RepositorioCategorias,
    RepositorioExistencias,
    RepositorioMovimientos,
    RepositorioProductos,
    RepositorioVentas,
)
from pos.aplicacion.sincronizacion import encolar_producto
from pos.dominio.errores import DatosProductoInvalidos
from pos.dominio.inventario import (
    ESTADO_AGOTADO,
    ESTADO_BAJO_MINIMO,
    ESTADO_GRANEL,
    ESTADO_NORMAL,
    MovimientoInventario,
    TipoMovimiento,
    estado_de_existencia,
)
from pos.dominio.productos import Producto, UnidadVenta

MOSTRAR = {
    "Todos": None,
    "Agotados": ESTADO_AGOTADO,
    "Bajo el mínimo": ESTADO_BAJO_MINIMO,
    "Normales": ESTADO_NORMAL,
    "Granel": ESTADO_GRANEL,
}
_URGENCIA = {ESTADO_AGOTADO: 0, ESTADO_BAJO_MINIMO: 1, ESTADO_NORMAL: 2, ESTADO_GRANEL: 3}


def _plano(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sin_tildes.lower()


@dataclass(frozen=True)
class FilaExistencia:
    codigo: str
    nombre: str
    categoria_id: int | None
    existencia: Decimal
    minimo: int | None
    ultima_venta: date | None
    estado: str
    granel: bool


@dataclass
class ConsultarExistencias:
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias
    repositorio_ventas: RepositorioVentas | None = None

    def ejecutar(
        self,
        buscar: str = "",
        categoria_id: int | None = None,
        mostrar: str = "Todos",
        orden: str = "Por urgencia",
        con_ultima_venta: bool = True,
    ) -> list[FilaExistencia]:
        """`con_ultima_venta=False` omite ese dato (caro con mucho historial) si no se muestra."""
        ultimas = (
            self.repositorio_ventas.ultima_venta_por_producto()
            if self.repositorio_ventas and con_ultima_venta
            else {}
        )
        # Una sola lectura de existencias si el repositorio la ofrece; si no, una por producto.
        todas = getattr(self.repositorio_existencias, "todas", None)
        existencias = todas() if todas is not None else None
        estado_pedido = MOSTRAR[mostrar]
        filas = []
        for producto in self.repositorio_productos.listar():
            if not producto.activo:
                continue
            if categoria_id is not None and producto.categoria_id != categoria_id:
                continue
            if buscar and _plano(buscar) not in _plano(f"{producto.nombre} {producto.codigo}"):
                continue
            if existencias is not None:
                existencia = existencias.get(producto.codigo)
            else:
                existencia = self.repositorio_existencias.obtener(producto.codigo)
            cantidad = existencia.cantidad if existencia else Decimal("0")
            granel = producto.unidad_venta is UnidadVenta.GRANEL
            estado = estado_de_existencia(cantidad, producto.stock_minimo, granel)
            if estado_pedido is not None and estado != estado_pedido:
                continue
            filas.append(
                FilaExistencia(
                    producto.codigo,
                    producto.nombre,
                    producto.categoria_id,
                    cantidad,
                    producto.stock_minimo,
                    ultimas.get(producto.codigo),
                    estado,
                    granel,
                )
            )
        if orden == "Nombre":
            filas.sort(key=lambda f: _plano(f.nombre))
        else:  # Por urgencia: agotados, bajo el minimo, normales, granel
            filas.sort(key=lambda f: (_URGENCIA[f.estado], _plano(f.nombre)))
        return filas


@dataclass
class DefinirStockMinimo:
    repositorio_productos: RepositorioProductos
    auditor: Auditor | None = None
    cola: ColaSincronizacion | None = None
    repositorio_categorias: RepositorioCategorias | None = None

    def ejecutar(self, codigo: str, minimo: int | None) -> Producto:
        producto = self.repositorio_productos.obtener_por_codigo(codigo)
        if producto is None:
            raise DatosProductoInvalidos(f"No existe un producto con código {codigo}")
        if minimo is not None and minimo < 0:
            raise DatosProductoInvalidos("El stock mínimo no puede ser negativo")
        if producto.unidad_venta is UnidadVenta.GRANEL and minimo is not None:
            raise DatosProductoInvalidos("Un producto a granel no lleva stock mínimo en unidades")
        anterior = producto.stock_minimo
        producto.stock_minimo = minimo
        self.repositorio_productos.guardar(producto)
        categoria = (
            self.repositorio_categorias.nombre_de(producto.categoria_id)
            if self.repositorio_categorias
            else None
        )
        encolar_producto(self.cola, producto, categoria)
        if self.auditor is not None and anterior != minimo:
            self.auditor.registrar(
                "Cambio de stock mínimo",
                f"{producto.nombre} ({codigo})",
                "—" if anterior is None else str(anterior),
                "—" if minimo is None else str(minimo),
            )
        return producto


@dataclass(frozen=True)
class FilaValorizada:
    codigo: str
    nombre: str
    existencia: Decimal
    unitario: int | None
    valor: int | None
    estado: str
    exclusion: str = ""  # por que no entra al total: «no valorizable» o «costo pendiente»


@dataclass(frozen=True)
class ResumenInventario:
    filas: list[FilaValorizada]
    total: int

    @property
    def excluidas(self) -> list[FilaValorizada]:
        return [f for f in self.filas if f.exclusion]


@dataclass
class ReporteInventario:
    repositorio_productos: RepositorioProductos
    repositorio_existencias: RepositorioExistencias

    def ejecutar(
        self,
        categoria_id: int | None = None,
        incluir: str = "Solo activos",
        valorizar_a: str = "Costo",
    ) -> ResumenInventario:
        filas = []
        for producto in self.repositorio_productos.listar():
            if incluir == "Solo activos" and not producto.activo:
                continue
            if categoria_id is not None and producto.categoria_id != categoria_id:
                continue
            existencia = self.repositorio_existencias.obtener(producto.codigo)
            cantidad = existencia.cantidad if existencia else Decimal("0")
            granel = producto.unidad_venta is UnidadVenta.GRANEL
            estado = estado_de_existencia(cantidad, producto.stock_minimo, granel)
            if granel:
                filas.append(
                    FilaValorizada(
                        producto.codigo,
                        producto.nombre,
                        cantidad,
                        None,
                        None,
                        estado,
                        "no valorizable",
                    )
                )
                continue
            unitario = (
                producto.precio.monto
                if valorizar_a == "Precio de venta"
                else (producto.costo.neto.monto if producto.costo else None)
            )
            if not unitario:  # sin costo cargado (o costo 0): no se valoriza en cero
                filas.append(
                    FilaValorizada(
                        producto.codigo,
                        producto.nombre,
                        cantidad,
                        None,
                        None,
                        estado,
                        "costo pendiente",
                    )
                )
                continue
            filas.append(
                FilaValorizada(
                    producto.codigo,
                    producto.nombre,
                    cantidad,
                    unitario,
                    int(cantidad * unitario),
                    estado,
                )
            )
        filas.sort(key=lambda f: (f.exclusion != "", -(f.valor or 0), _plano(f.nombre)))
        return ResumenInventario(filas, sum(f.valor for f in filas if f.valor is not None))


@dataclass
class ConsultarMovimientos:
    repositorio: RepositorioMovimientos
    repositorio_productos: RepositorioProductos

    def ejecutar(
        self,
        desde: date,
        hasta: date,
        tipo: TipoMovimiento | None = None,
        codigo: str | None = None,
    ) -> list[tuple[MovimientoInventario, str]]:
        """Movimientos del periodo, del mas reciente al mas antiguo, con el nombre del producto."""
        if hasta < desde:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        nombres: dict[str, str] = {}
        resultado = []
        for movimiento in self.repositorio.listar(desde, hasta, tipo, codigo):
            cod = movimiento.codigo_producto
            if cod not in nombres:
                producto = self.repositorio_productos.obtener_por_codigo(cod)
                nombres[cod] = producto.nombre if producto else cod
            resultado.append((movimiento, nombres[cod]))
        return resultado
