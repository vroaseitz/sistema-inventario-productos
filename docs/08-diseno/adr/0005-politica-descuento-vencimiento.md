# ADR 0005 — Política de descuento sugerido por vencimiento

- Estado: **aceptada** (definida por la Product Owner el 17-11-2026; actualizada el 18-11)
- Historias: HU-INV-02, HU-INV-03, HU-INV-06 · Hallazgo O-42

## Contexto
El sistema alerta los lotes próximos a vencer y sugiere un descuento. Hoy, cuando una vendedora ve un
producto cerca de vencer, pone un letrero de oferta y lo baja al 50 %. La primera propuesta del
equipo tenía tres tramos (30/20/10 %); la PO prefirió dos etapas y que se pudieran ajustar, porque «el
pan dura 2 semanas» y otros productos duran meses o un año.

## Decisión
- Consumo de stock **FEFO**: se vende primero el lote que vence antes.
- **Dos etapas por defecto:** 20 % desde 14 días antes de vencer y 50 % desde 7 días antes (etapa
  final). La PO resolvió el 18-11 que la etapa final es **1 semana** antes (era la duda abierta).
- **Editable por producto** en F2: días y porcentaje de cada etapa. Un campo vacío usa el valor por
  defecto. Se exige que la etapa final empiece más cerca del vencimiento que la primera, días ≥ 1 y
  porcentaje entre 1 y 100.
- Lote vencido: sin descuento (no debe venderse); se marca VENCIDO.
- El descuento es **solo una sugerencia**: F3 › Alertas y F1 muestran la misma cifra, y en F1 la
  vendedora la confirma o la ajusta antes de aplicarla. No cambia el precio del producto.

## Consecuencias
La política vive en `PoliticaDescuento` (`dominio/lotes.py`); cada `Producto` guarda sus cuatro
ajustes opcionales (`desc_dias_1`, `desc_pct_1`, `desc_dias_2`, `desc_pct_2`) y resuelve su política
con `politica_descuento()`. Los ajustes se guardan en la base local (SQLite); **falta replicarlos a
Supabase** (columnas nuevas en `pos.producto` y en el traductor de sincronización).
