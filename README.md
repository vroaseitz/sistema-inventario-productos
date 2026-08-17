# Sistema de Inventario de Productos

> Proyecto de Título — Documentación, integración y actualización de un sistema de gestión de inventario de productos.
>
> **Duoc UC** · Ingeniería en Informática · Capstone, 8.º semestre · Segundo semestre 2026
> Equipo: Victoria Roa · Eduardo Guzmán · Fernando Silva — Profesora guía: Karla Marilyn Roco

![Estado](https://img.shields.io/badge/estado-en%20planificación-yellow)
![Licencia](https://img.shields.io/badge/licencia-académica-blue)
![Rama principal](https://img.shields.io/badge/rama-main-green)

---

## Tabla de contenidos

- [Contexto y problema](#contexto-y-problema)
- [Objetivo general](#objetivo-general)
- [Objetivos específicos](#objetivos-específicos)
- [Alcance del trabajo](#alcance-del-trabajo)
- [Funcionalidades y actividades](#funcionalidades-y-actividades)
- [Tecnologías y herramientas previstas](#tecnologías-y-herramientas-previstas)
- [Metodología de trabajo](#metodología-de-trabajo)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Integrantes y responsabilidades](#integrantes-y-responsabilidades)
- [Cronograma y etapas](#cronograma-y-etapas)
- [Estado actual del proyecto](#estado-actual-del-proyecto)
- [Cómo contribuir](#cómo-contribuir)

---

## Contexto y problema

La gestión de inventario es un proceso crítico para cualquier organización que maneje productos físicos: determina la disponibilidad para la venta, el capital inmovilizado en bodega y la confiabilidad de la información que alimenta las decisiones de compra.

En muchas organizaciones este control se sostiene sobre planillas de cálculo compartidas, registros manuales y sistemas heredados que no conversan entre sí. Ese escenario produce problemas recurrentes:

| Problema | Consecuencia |
|---|---|
| Registro manual y descentralizado | Errores de digitación y descuadres entre el stock físico y el registrado |
| Ausencia de trazabilidad de movimientos | Imposible reconstruir quién movió qué producto y cuándo |
| Información desactualizada | Quiebres de stock no detectados a tiempo y sobrestock de baja rotación |
| Falta de alertas automáticas | Las reposiciones se gestionan de forma reactiva, no preventiva |
| Reportería inexistente o manual | Alto costo de tiempo para generar información de gestión |
| Sistema heredado sin documentación | Dependencia de conocimiento tácito; mantenimiento costoso y riesgoso |

**Problema a abordar:** la organización no cuenta con un sistema de inventario documentado, integrado y actualizado que garantice la exactitud del stock, la trazabilidad de los movimientos y la disponibilidad de información oportuna para la toma de decisiones.

---

## Objetivo general

Documentar, integrar y actualizar un sistema de inventario de productos que permita registrar y controlar de forma centralizada, trazable y confiable las existencias y sus movimientos, entregando información oportuna para la toma de decisiones operativas.

---

## Objetivos específicos

1. **Levantar y documentar** la situación actual del proceso de gestión de inventario, identificando actores, flujos, reglas de negocio y puntos críticos de falla.
2. **Especificar los requerimientos** funcionales y no funcionales del sistema, priorizados y validados con la contraparte.
3. **Diseñar la arquitectura y el modelo de datos** que soporte el registro de productos, existencias, movimientos y usuarios, junto con los diagramas correspondientes.
4. **Desarrollar los módulos** de gestión de productos, control de stock, registro de movimientos y reportería.
5. **Integrar el sistema** con las fuentes de datos y procesos existentes de la organización, definiendo el mecanismo de migración de la información histórica.
6. **Implementar control de acceso** por roles, resguardando la integridad y confidencialidad de la información.
7. **Verificar y validar** el sistema mediante pruebas unitarias, de integración y de aceptación con usuarios reales.
8. **Elaborar la documentación técnica y de usuario** que asegure la mantenibilidad del sistema más allá del término del proyecto.

---

## Alcance del trabajo

### Incluido en el alcance

- Levantamiento y documentación del proceso actual de gestión de inventario.
- Especificación de requerimientos funcionales y no funcionales.
- Diseño de la arquitectura de la solución y del modelo de datos.
- Desarrollo de los módulos definidos en la sección de funcionalidades.
- Integración con las fuentes de datos existentes y migración de datos históricos.
- Pruebas unitarias, de integración y de aceptación de usuario.
- Documentación técnica, manual de usuario y material de capacitación.
- Despliegue en un ambiente de prueba y entrega del plan de puesta en producción.

### Fuera del alcance

- Implementación de módulos contables, de facturación o de remuneraciones.
- Desarrollo de aplicación móvil nativa.
- Adquisición o instalación de hardware (lectores de código de barras, terminales, servidores).
- Operación y soporte del sistema en producción una vez finalizado el proyecto de título.
- Rediseño de procesos organizacionales ajenos a la gestión de inventario.

### Supuestos y restricciones

- La contraparte facilitará el acceso a la información y a las personas clave para el levantamiento.
- El proyecto se desarrolla dentro del período académico establecido por la institución.
- El equipo trabaja con las herramientas y licencias disponibles de forma gratuita o proporcionadas por la institución.

---

## Funcionalidades y actividades

### Módulos funcionales del sistema

| Módulo | Descripción |
|---|---|
| **Gestión de productos** | Alta, baja, modificación y consulta de productos; categorías, unidades de medida y códigos identificadores |
| **Control de existencias** | Consulta de stock en tiempo real por producto y ubicación; stock mínimo y máximo |
| **Movimientos de inventario** | Registro de entradas, salidas, traslados y ajustes, con fecha, responsable y motivo |
| **Trazabilidad** | Historial completo e inalterable de movimientos por producto |
| **Alertas** | Notificación automática ante stock bajo el mínimo, sobrestock o productos sin movimiento |
| **Reportería** | Informes de existencias, rotación, valorización y movimientos por período; exportación a Excel/PDF |
| **Gestión de usuarios y roles** | Autenticación y autorización diferenciada (administrador, bodeguero, consulta) |
| **Auditoría** | Bitácora de acciones realizadas por cada usuario dentro del sistema |

### Actividades del proyecto

- Reuniones de levantamiento con la contraparte y usuarios del proceso.
- Modelamiento de procesos (AS-IS y TO-BE).
- Elaboración del documento de especificación de requerimientos.
- Diseño de diagramas UML: casos de uso, clases, secuencia y despliegue.
- Diseño del modelo entidad-relación de la base de datos.
- Desarrollo iterativo de los módulos y revisiones de código entre pares.
- Diseño y ejecución del plan de pruebas.
- Capacitación a usuarios y elaboración de manuales.
- Preparación de la defensa del proyecto de título.

---

## Tecnologías y herramientas previstas

> **Nota:** el stack técnico definitivo se encuentra **en definición**. Esta sección se actualizará una vez que el equipo cierre la decisión durante la Etapa 2 (Análisis y diseño). Las opciones en evaluación se listan a continuación.

| Categoría | Alternativas en evaluación |
|---|---|
| Lenguaje / backend | Python (Django o Flask) · Java (Spring Boot) · Node.js (Express o NestJS) |
| Frontend | React · Vue · Plantillas del lado del servidor |
| Base de datos | PostgreSQL · MySQL · SQL Server |
| Control de versiones | Git + GitHub |
| Gestión del trabajo | GitHub Projects / Issues |
| Modelado | draw.io · StarUML · dbdiagram.io |
| Pruebas | Framework de pruebas unitarias correspondiente al stack elegido |
| Documentación | Markdown en el repositorio · Microsoft Word para las entregas formales |
| Comunicación | Correo institucional · Reuniones periódicas del equipo |

**Criterios de selección del stack:** experiencia previa del equipo, disponibilidad de licencias gratuitas, compatibilidad con la infraestructura de la contraparte y facilidad de mantenimiento posterior.

---

## Metodología de trabajo

El proyecto se desarrolla bajo un enfoque **ágil iterativo e incremental**, adaptado al contexto académico.

### Principios

- **Iteraciones (sprints) de 2 semanas**, cada una con un incremento funcional demostrable.
- **Reuniones de planificación** al inicio de cada iteración para definir el compromiso del período.
- **Reuniones de seguimiento semanales** para revisar avances y levantar impedimentos.
- **Revisión y retrospectiva** al cierre de cada iteración.
- **Validación continua** con la contraparte y con el profesor guía.

### Flujo de trabajo en Git

Se utiliza un flujo basado en ramas de funcionalidad:

```
main          ← rama estable; solo recibe merges revisados
 └── develop  ← rama de integración del equipo
      ├── feature/<nombre-funcionalidad>
      ├── fix/<nombre-correccion>
      └── docs/<nombre-documento>
```

**Reglas acordadas:**

1. No se hace *commit* directo sobre `main`.
2. Toda incorporación se realiza mediante *Pull Request* con al menos una revisión de otro integrante.
3. Los mensajes de commit siguen el formato [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
4. Las tareas se gestionan como *Issues* y se vinculan a su *Pull Request* correspondiente.
5. Ningún archivo con credenciales, tokens o datos sensibles se sube al repositorio.

---

## Estructura del repositorio

```
sistema-inventario-productos/
│
├── docs/                    Documentación académica del proyecto
│   ├── propuesta/           Propuesta y anteproyecto
│   ├── avances/             Informes de avance por etapa
│   ├── diagramas/           Diagramas UML, ER y de procesos
│   ├── actas/               Actas de reunión del equipo y con la contraparte
│   └── informe-final/       Informe final y material de defensa
│
├── src/                     Código fuente
│   ├── backend/             Lógica de negocio y API
│   ├── frontend/            Interfaz de usuario
│   └── shared/              Componentes y utilidades compartidas
│
├── database/                Capa de datos
│   ├── modelo/              Modelo entidad-relación y diccionario de datos
│   ├── migraciones/         Scripts de versionado del esquema
│   └── scripts/             Consultas, carga inicial y migración de datos
│
├── tests/                   Pruebas automatizadas
│   ├── unitarias/
│   └── integracion/
│
├── scripts/                 Utilidades de apoyo y automatización
├── assets/                  Recursos gráficos
│   ├── imagenes/
│   └── capturas/
│
├── config/                  Plantillas de configuración (sin credenciales)
├── .github/                 Plantillas de issues y flujos de trabajo
├── .gitignore
└── README.md
```

---

## Integrantes y responsabilidades

El equipo está conformado por tres integrantes. Si bien cada uno tiene un **foco principal** de trabajo, el equipo acordó que **todos participan y revisan todas las áreas del proyecto**: nadie queda como único responsable de una parte, de modo que el conocimiento sea compartido y ningún avance dependa de una sola persona.

| Integrante | Usuario GitHub | Foco principal | Responsabilidades |
|---|---|---|---|
| **Victoria Roa** | [`@vroaseitz`](https://github.com/vroaseitz) | Documentación y análisis | Documentación académica y técnica, levantamiento de requerimientos, actas de reunión, informes de avance e informe final. Coordinación de entregas |
| **Eduardo Guzmán** | *(por definir)* | Documentación y desarrollo | Apoyo transversal en ambas áreas: participa en el desarrollo de módulos y en la elaboración de la documentación. Nexo entre el diseño documentado y la implementación |
| **Fernando Silva** | [`@fernandosilvot`](https://github.com/fernandosilvot) | Desarrollo | Arquitectura de la solución, modelo de datos, desarrollo de los módulos del sistema, integraciones y despliegue |

### Acuerdos de trabajo del equipo

- Toda entrega es **revisada por al menos un integrante distinto** al que la elaboró.
- Las responsabilidades detalladas por etapa se registran en las actas de reunión (`docs/actas/`) y se ajustan según el avance del proyecto.
- La distribución anterior es de **foco**, no de exclusividad: los tres integrantes deben poder explicar y defender cualquier parte del trabajo.

### Contexto académico

| | |
|---|---|
| **Institución** | Duoc UC |
| **Carrera** | Ingeniería en Informática |
| **Nivel** | 8.º semestre |
| **Asignatura** | Capstone — Proyecto de Título |
| **Profesora guía** | Karla Marilyn Roco |
| **Período** | Segundo semestre 2026 |

---

## Cronograma y etapas

| Etapa | Descripción | Entregable | Estado |
|---|---|---|---|
| **1. Planificación** | Definición del problema, objetivos, alcance y conformación del equipo | Propuesta de proyecto | 🟡 En curso |
| **2. Análisis y diseño** | Levantamiento del proceso actual, requerimientos, arquitectura, modelo de datos y definición del stack | Documento de especificación y diagramas | ⚪ Pendiente |
| **3. Desarrollo — Iteración 1** | Módulos de gestión de productos y control de existencias | Incremento funcional 1 | ⚪ Pendiente |
| **4. Desarrollo — Iteración 2** | Movimientos de inventario, trazabilidad y alertas | Incremento funcional 2 | ⚪ Pendiente |
| **5. Desarrollo — Iteración 3** | Reportería, gestión de usuarios y auditoría | Incremento funcional 3 | ⚪ Pendiente |
| **6. Integración y migración** | Conexión con fuentes de datos existentes y carga de información histórica | Sistema integrado | ⚪ Pendiente |
| **7. Pruebas y validación** | Pruebas unitarias, de integración y de aceptación con usuarios | Informe de pruebas | ⚪ Pendiente |
| **8. Documentación y cierre** | Manuales, capacitación, informe final y defensa | Informe final y presentación | ⚪ Pendiente |

> Las fechas específicas de cada etapa se incorporarán una vez confirmado el calendario académico del período.

**Leyenda:** 🟢 Completado · 🟡 En curso · ⚪ Pendiente

---

## Estado actual del proyecto

**Etapa 1 — Planificación · En curso**

El proyecto se encuentra en su fase inicial. A la fecha se ha realizado lo siguiente:

- ✅ Definición preliminar del problema, objetivo general y objetivos específicos.
- ✅ Delimitación del alcance del trabajo.
- ✅ Creación del repositorio y de la estructura base del proyecto.
- ✅ Definición de la metodología de trabajo y del flujo de ramas en Git.
- ✅ Conformación del equipo y definición del foco de trabajo de cada integrante.
- 🟡 Formalización detallada de responsabilidades por etapa (se registra en `docs/actas/`).
- ⚪ Levantamiento del proceso actual con la contraparte.
- ⚪ Definición del stack tecnológico.

**Próximos pasos:** agendar las reuniones de levantamiento con la contraparte, cerrar la decisión del stack tecnológico y levantar el proceso actual para dar inicio a la Etapa 2.

---

## Cómo contribuir

Este repositorio es de uso académico y las contribuciones están restringidas a los integrantes del equipo.

```bash
# 1. Clonar el repositorio
git clone https://github.com/vroaseitz/sistema-inventario-productos.git
cd sistema-inventario-productos

# 2. Crear una rama para tu tarea
git checkout -b feature/nombre-de-la-funcionalidad

# 3. Trabajar y confirmar los cambios
git add .
git commit -m "feat: descripción breve del cambio"

# 4. Subir la rama y abrir un Pull Request
git push -u origin feature/nombre-de-la-funcionalidad
```

### Antes de cada commit

- [ ] No se incluyen archivos `.env`, credenciales, tokens ni claves privadas.
- [ ] El mensaje de commit sigue el formato acordado.
- [ ] Los cambios fueron probados localmente.
- [ ] La documentación afectada fue actualizada.

---

<sub>Proyecto de Título — Documento vivo. Última actualización: agosto de 2026.</sub>
