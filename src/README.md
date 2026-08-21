# Código fuente

| Carpeta | Contenido |
| --- | --- |
| `app/` | Aplicación de escritorio: punto de venta e inventario |
| `migracion/` | Proceso de migración única desde la base Firebird del sistema antiguo |
| `shared/` | Código compartido entre ambos |

> El stack tecnológico está **pendiente de definición**. Restricciones: Windows, conexión a Supabase, empaquetable como instalador.
>
> Ninguna credencial debe quedar escrita en el código. Usar variables de entorno según `config/.env.example`.
