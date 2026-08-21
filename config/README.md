# Configuración

Plantillas de configuración del proyecto.

| Archivo | Contenido |
| --- | --- |
| `.env.example` | Plantilla de variables de entorno, **sin valores reales** |

## Uso

Copiar la plantilla a la raíz del proyecto y completar los valores del entorno propio:

```bash
cp config/.env.example .env
```

> ⚠️ El archivo `.env` está excluido por `.gitignore` y **nunca debe subirse**. Aquí solo viven plantillas sin credenciales.
>
> Separar las variables de entorno del código es uno de los mecanismos comprometidos como equivalente a la excepción de contenedores.
