# Sprint 3 — Plan de pareo: Módulo de productos (alta, edición y baja)

Tarea ClickUp: "Módulo de productos — alta, edición y baja" (asignada a Eduardo).

## Lo que ya existe (no hay que rehacerlo)

- `src/pos/dominio/productos.py`: entidad `Producto`, ya tiene el campo `activo: bool` listo para dar de baja (soft delete).
- `src/pos/infraestructura/sqlite/repositorio_productos.py`: `guardar()` ya es un *upsert* (`INSERT ... ON CONFLICT DO UPDATE`) — sirve tanto para crear como para editar/dar de baja, sin tocar SQL.
- `src/pos/aplicacion/casos_uso/registrar_producto.py`: caso de uso de **alta**, ya funciona y tiene tests (`tests/unitarias/test_casos_uso.py`).
- `src/pos/interfaz/app_tkinter.py`: `VentanaProductos` ya tiene el formulario de alta y la tabla (`Treeview`) que lista productos.

## Lo que falta (el trabajo real de esta tarea)

### 1. Caso de uso: editar producto
Nuevo archivo `src/pos/aplicacion/casos_uso/editar_producto.py`, mismo patrón que `registrar_producto.py`:

```python
@dataclass
class EditarProducto:
    repositorio: RepositorioProductos

    def ejecutar(self, codigo: str, nombre: str, precio: int, categoria_id: int | None = None) -> Producto:
        producto = self.repositorio.obtener_por_codigo(codigo)
        if producto is None:
            raise DatosProductoInvalidos(f"No existe un producto con codigo {codigo}")
        producto.nombre = nombre
        producto.precio = Dinero(precio)
        producto.categoria_id = categoria_id
        self.repositorio.guardar(producto)
        return producto
```
(`Producto` es un `@dataclass` mutable, así que reasignar campos y volver a guardar funciona directo.)

### 2. Caso de uso: dar de baja
Nuevo archivo `src/pos/aplicacion/casos_uso/dar_de_baja_producto.py`:

```python
@dataclass
class DarDeBajaProducto:
    repositorio: RepositorioProductos

    def ejecutar(self, codigo: str) -> Producto:
        producto = self.repositorio.obtener_por_codigo(codigo)
        if producto is None:
            raise DatosProductoInvalidos(f"No existe un producto con codigo {codigo}")
        producto.activo = False
        self.repositorio.guardar(producto)
        return producto
```

### 3. Tests unitarios
`tests/unitarias/test_casos_uso.py` ya tiene el patrón para `RegistrarProducto` con un repositorio fake en memoria — copiar el mismo estilo para `EditarProducto` y `DarDeBajaProducto` (caso feliz + caso "no existe el código").

### 4. GUI — extender `VentanaProductos`
En `src/pos/interfaz/app_tkinter.py`:
- Recibir `editar_producto: EditarProducto` y `dar_de_baja: DarDeBajaProducto` en el constructor (mismo patrón que `registrar_producto`).
- Al seleccionar una fila de la tabla (`<<TreeviewSelect>>`), cargar sus datos en el formulario y cambiar el botón "Agregar" por "Guardar cambios" (llama a `editar_producto.ejecutar`).
- Agregar un botón "Dar de baja" que llame a `dar_de_baja.ejecutar(codigo_seleccionado)` y refresque la tabla.
- Filtrar la tabla para no listar productos con `activo=False` (o mostrarlos tachados/grises — decisión de UX simple, no bloqueante).

### 5. Conectar en `__main__.py`
Instanciar `EditarProducto(repositorio)` y `DarDeBajaProducto(repositorio)` junto a `registrar`, y pasarlos a `VentanaProductos(...)`.

## Definition of Done de esta tarea

- [ ] `pytest` sigue en verde (casos nuevos incluidos).
- [ ] `ruff check .` sin errores.
- [ ] Se puede crear, editar y dar de baja un producto desde la GUI, y el cambio persiste en SQLite (verificable reabriendo la app).
- [ ] Commit hecho desde la cuenta de Eduardo en GitHub.

## Cómo trabajar la sesión

1. Eduardo escribe el código (los 2 casos de uso + tests) — Fernando acompaña explicando el patrón, sin escribir por él.
2. Juntos extienden la GUI (paso 4) — es la parte más visual, útil para pantear.
3. Eduardo corre `pytest` y `ruff check .` localmente, y hace el commit desde su cuenta.
