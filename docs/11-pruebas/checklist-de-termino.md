# Checklist de término — Emporio NaturalSur

**Fecha:** 19-11-2026 (actualizado; la primera versión es del 11-11) · **Equipo:** Silva, Guzmán, Roa · ✅ = verificado; ⚠️ = parcial o pendiente.

## 1. Entregables

| Entregable | Estado | Dónde |
|---|---|---|
| Plan de pruebas y evidencias | ✅ | `Fase 2/Evidencias de Proyecto/` |
| Casos de prueba | ✅ | `docs/11-pruebas/casos-de-prueba.md` |
| Registro de defectos por ciclos | ✅ | `docs/11-pruebas/registro-de-defectos.md` |
| Manual de implementación | ✅ | `docs/12-despliegue/manual-de-implementacion.md` |
| Manual de usuario final | ✅ | `docs/manual-usuario/manual-de-usuario.md` (sin capturas de Catálogo, cupo ni anulación) |
| Video demostrativo (≤ 5 min) | ✅ | `docs/video/e2e-hyperframes/` (4:09; la licencia de la música no está confirmada, entregar la versión sin música) |
| Guía E2E de la demo | ✅ | `docs/11-pruebas/guia-e2e-demo.md` |
| Presentación final (PPT, 13 contenidos, oral en inglés) | ⚠️ Pendiente | falta el formato del campus |
| Diario de reflexión Fase 3 (3.1) y Autoevaluación (3.2) | ⚠️ Pendiente | personales de cada integrante |
| Todo en GitHub y OneDrive | ⚠️ | faltan commit/push de los documentos nuevos y subir a OneDrive |

## 2. Funcionalidad

| Punto | Estado |
|---|---|
| Venta, caja, descuentos, crédito, cupo, anulación (F1, F4) | ✅ probado (automático y manual) |
| Catálogo, inventario, lotes y alertas (F2, F3) | ✅ |
| Compras (F5), reportes (F6), administración y auditoría (F7) | ✅ |
| Sincronización con Supabase | ⚠️ aplicar migraciones 009 y 010 y probar con la `.env` real; ya sincroniza al cerrar la jornada y aparta lo rechazado |
| Migración de datos del sistema antiguo | ✅ importador probado con los CSV reales; ⚠️ falta ensayarlo en la VM y definir el corte (ver `docs/12-despliegue/plan-de-implantacion-20-11.md`) |
| `.exe` en Windows 8.1 | ⚠️ probado el 08-11; recompilar con el código nuevo y volver a probar |
| Impresora real | ⚠️ no probada (falta el equipo) |

## 3. Pruebas y calidad

- ✅ 530 pruebas automáticas pasan en `fix/qa-18-11` con PostgreSQL real (≈ 23 s), incluidos los flujos E2E de interfaz y el de migración. En `develop` pasan 459.
- ✅ Los 94 defectos registrados están corregidos: 50 cerrados por QA y 44 esperando su re-prueba.
- ⚠️ Falta la re-prueba de QA de los 44 corregidos y confirmar con QA la prioridad y clasificación de CO-07, CO-08, CL-07 e I-07.

## 4. Integración y cierre

- ⚠️ Todas las ramas están unificadas en `develop`; falta el PR `develop → main`.
- ⚠️ Confirmar la fecha de presentación (campus: 30-11, 14:30–19:00; antes se anotó 27-11) y el ensayo del 16-11.
- ⚠️ Cada PR lo debe aprobar el otro desarrollador.
