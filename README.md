# Proyecto de Título – Actualización del Sistema de Inventario de Productos

## Emporio NaturalSur

## 📌 Descripción del proyecto

Este proyecto corresponde al **Proyecto de Título de Ingeniería en Informática de Duoc UC**, desarrollado para **Emporio NaturalSur**, minimarket dedicado a la comercialización de productos naturales y gourmet.

El objetivo principal del proyecto es **analizar, actualizar y mejorar el sistema de gestión e inventario de productos utilizado actualmente por el negocio**, debido a que presenta errores, limitaciones y problemas relacionados con la administración y consistencia de la información.

El proyecto busca modernizar el sistema existente y mejorar la forma en que se gestionan los productos, sus características, precios, categorías, unidades de venta, stock y estados.

Como parte del proyecto, también se considera la **posible integración con la página web de Emporio NaturalSur**, actualmente en proceso de desarrollo y que ya cuenta con un avance considerable. Esta integración se evaluará según las necesidades y alcance definido para el Proyecto de Título.

> **Importante:** el objetivo principal del proyecto es la **actualización y mejora del sistema de inventario y gestión de productos**. La página web constituye un componente complementario que podría integrarse al sistema, pero no representa el objetivo principal del proyecto.

---

## 📑 Contenido

- [🎯 Objetivo general](#-objetivo-general)
- [🔎 Problemática actual](#-problemática-actual)
- [💡 Propuesta de solución](#-propuesta-de-solución)
- [🔄 Integración con la página web](#-integración-con-la-página-web)
- [🗄️ Gestión de datos](#️-gestión-de-datos)
- [🏗️ Tecnologías consideradas](#️-tecnologías-consideradas)
- [📦 Productos](#-productos)
- [🏷️ Estados de productos](#️-estados-de-productos)
- [👥 Equipo](#-equipo)
- [📋 Enfoque del Proyecto de Título](#-enfoque-del-proyecto-de-título)
- [🔗 Trazabilidad del proyecto](#-trazabilidad-del-proyecto)
- [🚧 Alcance inicial](#-alcance-inicial)
- [📈 Resultados esperados](#-resultados-esperados)
- [📚 Documentación del proyecto](#-documentación-del-proyecto)
- [📂 Estructura del repositorio](#-estructura-del-repositorio)
- [⚠️ Estado actual del proyecto](#️-estado-actual-del-proyecto)
- [📝 Nota para desarrollo con IA](#-nota-para-desarrollo-con-ia)

---

## 🎯 Objetivo general

Actualizar y mejorar el sistema de gestión e inventario de productos de Emporio NaturalSur, mediante la revisión de su funcionamiento actual, corrección de errores, mejora de la estructura y calidad de los datos, y la incorporación de mecanismos que permitan una administración más eficiente y consistente de la información de productos.

---

## 🔎 Problemática actual

El sistema actual presenta diferentes dificultades que afectan la gestión de los productos del negocio.

Entre los principales problemas identificados se encuentran:

* Errores en la información de productos.
* Productos faltantes.
* Productos duplicados.
* Productos sin imágenes.
* Productos sin descripción.
* Precios incorrectos o vacíos.
* Información inconsistente.
* Dificultades para mantener actualizados los productos.
* Diferencias entre la información del sistema interno y la información utilizada por la plataforma web.
* Limitaciones en la administración de productos.
* Dificultades para gestionar correctamente productos vendidos por unidad y productos vendidos a granel.

Estos problemas pueden generar información incorrecta o desactualizada y dificultar la administración diaria del negocio.

---

## 💡 Propuesta de solución

El proyecto contempla analizar el sistema actual y posteriormente diseñar e implementar mejoras orientadas principalmente a la **gestión de productos e inventario**.

La solución podrá contemplar:

* Reestructuración o mejora del modelo de datos.
* Corrección y depuración de información.
* Gestión de productos.
* Gestión de códigos de productos.
* Gestión de nombres y descripciones.
* Gestión de marcas.
* Gestión de categorías y subcategorías.
* Gestión de unidades de venta.
* Gestión de productos a granel.
* Gestión de precios.
* Gestión de stock.
* Control del estado de los productos.
* Gestión de imágenes.
* Validación de información.
* Detección y prevención de datos duplicados.
* Mejoras en los procesos de administración.
* Pruebas de funcionamiento y calidad de los datos.

La implementación definitiva dependerá de los requerimientos levantados durante el desarrollo del proyecto.

---

## 🔄 Integración con la página web

Emporio NaturalSur cuenta con una página web que se encuentra actualmente en proceso de desarrollo y presenta un avance considerable.

La página contempla funcionalidades relacionadas con:

* Catálogo de productos.
* Categorías y subcategorías.
* Carrito de compras.
* Usuarios y autenticación.
* Gestión de productos.
* Productos vendidos por unidad.
* Productos vendidos a granel.
* Panel administrativo.
* Información de contacto y ayuda.

Como parte del proyecto se evaluará la conexión entre el **sistema de inventario** y la **plataforma web**, con el objetivo de evitar inconsistencias y facilitar la disponibilidad de información actualizada.

La arquitectura considerada inicialmente es:

```text
Sistema interno / Inventario
          ↓
Proceso de transformación y limpieza
          ↓
Base de datos central
          ↓
Sistema web
```

La implementación de esta integración estará sujeta a los requerimientos, factibilidad técnica y alcance definido para el Proyecto de Título.

---

## 🗄️ Gestión de datos

Uno de los componentes importantes del proyecto corresponde a mejorar la calidad y estructura de los datos de productos.

Actualmente se considera trabajar con información proveniente del sistema interno del negocio y adaptarla a las necesidades del sistema actualizado.

El proyecto podrá utilizar un proceso de transformación y limpieza de datos bajo un enfoque **ETL**:

```text
Extract
  ↓
Transform
  ↓
Load
```

### Extract

Obtención de información desde el sistema interno del negocio.

### Transform

Proceso de limpieza, validación y adaptación de los datos.

Entre las posibles transformaciones se encuentran:

* Normalización de nombres.
* Validación de precios.
* Validación de códigos.
* Eliminación o detección de duplicados.
* Clasificación de categorías.
* Validación de unidades.
* Identificación de información faltante.
* Adaptación de los datos al modelo definido para el sistema.

### Load

Carga de los datos procesados hacia la base de datos utilizada por el sistema actualizado.

---

## 🏗️ Tecnologías consideradas

Las tecnologías pueden modificarse durante el desarrollo dependiendo de los requerimientos y decisiones técnicas.

### Base de datos

* Supabase
* PostgreSQL

### Sistema web

* Tecnologías web actualmente utilizadas por el proyecto existente.
* Integración con Supabase.

### Sistema interno

* Firebird, como fuente de información del sistema actual del negocio.

### Herramientas de desarrollo y gestión

* Git
* GitHub
* Cursor
* Herramientas de documentación y modelamiento.
* Herramientas de pruebas.

---

## 📦 Productos

El sistema debe permitir diferenciar entre productos vendidos por unidad y productos vendidos a granel.

Para los productos a granel se consideran actualmente atributos como:

```text
is_bulk
bulk_unit
bulk_min_amount
bulk_step
bulk_base_amount
bulk_base_price
bulk_quick_amounts
```

Estos campos serán revisados durante el proyecto para determinar si la estructura actual es adecuada o requiere modificaciones.

---

## 🏷️ Estados de productos

La propuesta actual contempla los siguientes estados:

| Estado         | Descripción                                         |
| -------------- | --------------------------------------------------- |
| `draft`        | Producto importado o creado, pendiente de revisión. |
| `active`       | Producto publicado y disponible.                    |
| `hidden`       | Producto oculto temporalmente.                      |
| `discontinued` | Producto que ya no se comercializa.                 |

El estado **agotado** no necesariamente será almacenado como un estado independiente, ya que puede determinarse a partir de la información de stock cuando corresponda.

Esta definición podrá modificarse según los requerimientos levantados y las reglas de negocio identificadas.

---

## 👥 Equipo

Proyecto desarrollado por:

| Integrante | Usuario GitHub |
| --- | --- |
| **Victoria Roa Seitz** | [`@vroaseitz`](https://github.com/vroaseitz) |
| **Eduardo Andrés Guzmán Manquehual** | [`@eg-andreszx`](https://github.com/eg-andreszx) |
| **Fernando Silva** | [`@fernandosilvot`](https://github.com/fernandosilvot) |

Proyecto de Título – Ingeniería en Informática
Duoc UC · 8.º semestre · **Sección 005D** · Segundo semestre 2026
Profesora guía: **Karla Marilyn Roco**

---

## 📋 Enfoque del Proyecto de Título

El proyecto busca abordar el problema desde una perspectiva integral y no únicamente desde el desarrollo de software.

Las principales áreas de trabajo serán:

* Levantamiento de requerimientos.
* Análisis del sistema actual.
* Identificación de problemas.
* Modelamiento de procesos.
* Diseño de solución.
* Diseño y gestión de base de datos.
* Calidad de datos.
* Procesos ETL.
* Gestión de productos.
* Integración de sistemas.
* Desarrollo de software.
* Pruebas.
* Documentación.
* Gestión del proyecto.

La solución deberá estar respaldada por requerimientos, criterios de aceptación, pruebas y evidencias que permitan demostrar el cumplimiento de los objetivos establecidos.

---

## 🔗 Trazabilidad del proyecto

Durante el desarrollo se buscará mantener trazabilidad entre:

```text
Problema
   ↓
Requerimiento
   ↓
Diseño
   ↓
Implementación
   ↓
Prueba
   ↓
Resultado
```

Esto permitirá justificar cada funcionalidad implementada y evitar incorporar elementos que no aporten directamente a los objetivos del proyecto.

---

## 🚧 Alcance inicial

### Incluido

* Análisis del sistema actual.
* Levantamiento de requerimientos.
* Análisis de problemas de gestión de productos.
* Revisión de la estructura de datos.
* Mejora del sistema de inventario.
* Gestión de productos.
* Calidad y consistencia de datos.
* Gestión de stock.
* Gestión de precios.
* Gestión de categorías.
* Gestión de productos a granel.
* Pruebas.
* Documentación.
* Evaluación de integración con la página web.

### Fuera del alcance inicial

Las siguientes funcionalidades no forman parte del objetivo principal y solo podrán considerarse como trabajo futuro o si los requerimientos justifican su incorporación:

* Implementación de medios de pago en línea.
* Automatizaciones avanzadas de WhatsApp.
* Inteligencia artificial.
* Sistemas de recomendación.
* Funcionalidades que no estén relacionadas directamente con la gestión de productos e inventario.
* Desarrollo de una página web completamente nueva.

---

## 📈 Resultados esperados

Al finalizar el proyecto se espera contar con un sistema de gestión de productos e inventario más:

* Organizado.
* Consistente.
* Confiable.
* Mantenible.
* Escalable.
* Fácil de administrar.

Además, se espera reducir los problemas relacionados con información duplicada, incompleta o inconsistente y mejorar la disponibilidad de información para los procesos que dependan de los productos.

En caso de implementarse la integración con la plataforma web, se espera además reducir las diferencias entre la información utilizada por el sistema interno y la información disponible en la web.

---

## 📚 Documentación del proyecto

La documentación del Proyecto de Título deberá incluir, entre otros elementos:

* Diagnóstico del sistema actual.
* Levantamiento de requerimientos.
* Requerimientos funcionales y no funcionales.
* Modelamiento de procesos.
* Modelo de datos.
* Diseño de arquitectura.
* Diseño de solución.
* Proceso ETL.
* Planificación.
* Pruebas.
* Resultados.
* Evidencias.
* Manuales y documentación técnica.
* Conclusiones y trabajo futuro.

---

## 📂 Estructura del repositorio

```text
sistema-inventario-productos/
│
├── docs/                    Documentación del Proyecto de Título
│   ├── diagnostico/         Diagnóstico del sistema actual
│   ├── requerimientos/      Levantamiento y requerimientos funcionales y no funcionales
│   ├── modelamiento/        Modelamiento de procesos y diseño de solución
│   ├── diagramas/           Diagramas y modelo de datos
│   ├── actas/               Actas de reunión del equipo y con la contraparte
│   ├── avances/             Informes de avance
│   └── informe-final/       Informe final y material de defensa
│
├── src/                     Código fuente
│   ├── etl/                 Proceso Extract · Transform · Load
│   └── shared/              Utilidades y modelos compartidos
│
├── database/                Capa de datos
│   ├── modelo/              Modelo de datos y diccionario de datos
│   ├── migraciones/         Scripts de versionado del esquema
│   └── scripts/             Consultas de apoyo y depuración de información
│
├── tests/                   Pruebas
│   ├── unitarias/
│   └── integracion/
│
├── scripts/                 Utilidades de apoyo
├── assets/                  Recursos gráficos
│   ├── imagenes/
│   └── capturas/
│
├── config/                  Plantillas de configuración (sin credenciales)
├── .gitignore
└── README.md
```

### Convenciones de trabajo

* Rama `main`: estable, solo recibe cambios revisados.
* Rama `develop`: integración del trabajo del equipo.
* Ramas de trabajo: `feature/<nombre>`, `fix/<nombre>`, `docs/<nombre>`.
* Mensajes de commit según [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
* **No se suben credenciales al repositorio.** Esto incluye las credenciales de conexión al sistema interno y las llaves de Supabase.

---

## ⚠️ Estado actual del proyecto

**Estado:** En etapa de definición y levantamiento de requerimientos.

El alcance, arquitectura definitiva, modelo de datos y funcionalidades finales aún pueden modificarse a medida que avance el levantamiento de información y se validen las necesidades reales del negocio.

Las decisiones técnicas deberán estar justificadas por los requerimientos del proyecto y no únicamente por factibilidad o preferencia tecnológica.

---

## 📝 Nota para desarrollo con IA

Este repositorio corresponde a un **Proyecto de Título académico**.

Antes de implementar nuevas funcionalidades:

1. Identificar el problema que se busca solucionar.
2. Verificar si existe un requerimiento asociado.
3. Evaluar si la funcionalidad pertenece al alcance.
4. Analizar impacto en la arquitectura y base de datos.
5. Considerar compatibilidad con el sistema existente.
6. Definir cómo será probada.
7. Documentar los cambios realizados.

No implementar funcionalidades únicamente porque sean técnicamente posibles o visualmente atractivas.

La prioridad debe ser **resolver los problemas reales del sistema de inventario y gestión de productos de Emporio NaturalSur**.
