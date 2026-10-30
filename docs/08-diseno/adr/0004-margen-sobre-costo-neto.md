# ADR 0004 — El margen se calcula sobre el costo NETO

- **Estado:** Propuesto por Fernando Silva (28-10-2026), a ratificar por el equipo
- **Contexto:** el dominio (`Producto.margen`, `Producto.markup`) usa el costo **neto**; el
  prototipo navegable muestra el margen con el costo **total** (neto + IVA + impuesto
  adicional). Hay que fijar uno solo, porque reportes, ficha de producto, alerta de
  vencimiento y descuento sugerido deben mostrar la misma cifra para el mismo producto.

## Decisión

**Margen y markup se calculan sobre el costo neto, en todo el sistema.** El costo total se
muestra solo como dato informativo («costo con IVA»), nunca como base del margen.

## Por qué

1. **El IVA crédito es recuperable.** El negocio no «gasta» el IVA de compra: lo descuenta del
   IVA de venta. Restarlo del precio de venta subestima la ganancia real. Es exactamente el
   defecto del sistema legado que HU-PRD-02 corrige («el costo consolidado impedía
   recuperar el IVA crédito y distorsionaba el margen»).
2. **El precio de venta incluye IVA; el costo neto no.** Para comparar peras con peras, el
   precio también debe llevarse a neto: `margen = (precio_neto - costo_neto) / precio_neto`.
   Hoy el dominio compara `precio` (con IVA) contra `costo_neto`; **queda como corrección
   pendiente** alinear esa fórmula (ver «Consecuencias»).
3. Ya está implementado y probado en `Producto.margen`/`markup` (HU-PRD-03, HU-PRD-08).

## Consecuencias

- El prototipo (v3) debe corregirse para mostrar margen sobre neto; el costo total queda
  como etiqueta secundaria.
- **Pendiente de decidir con la Product Owner:** si el precio de venta se considera con IVA
  incluido (lo habitual en un emporio minorista en Chile). En ese caso la fórmula correcta
  usa el precio neto (`precio / 1,19`). Mientras no se confirme, el sistema mantiene la
  fórmula actual y esta ADR no la modifica.
- Eduardo debe guardar neto, IVA e impuesto adicional por separado (hallazgo C-05b): hoy la
  lectura reconstruye el IVA como 19 % del neto, lo que oculta cualquier IVA distinto.
