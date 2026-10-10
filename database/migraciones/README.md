# Migraciones de esquema

Scripts versionados que modifican la estructura de la base de datos.

## Convención

```text
001_crear_tabla_productos.sql
002_agregar_campos_granel.sql
003_crear_tabla_ventas.sql
```

Numeración correlativa, nombre descriptivo, y **nunca se modifica una migración ya aplicada**: si algo cambia, se crea una nueva.

## Tipos que se registran aquí

- **Migraciones de esquema**: cambios de estructura durante el desarrollo
- **Migraciones correctivas**: ajustes posteriores al arranque, si se detectan inconsistencias

> La migración **de datos** desde el sistema antiguo es otra cosa y se documenta en `docs/09-plan-migracion/`.
