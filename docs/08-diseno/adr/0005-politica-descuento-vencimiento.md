# ADR 0005 — Politica de descuento sugerido por vencimiento

- Estado: **propuesta, a validar con la Product Owner**
- Historias: HU-INV-02, HU-INV-03, HU-INV-06

## Contexto
El sistema debe alertar los lotes proximos a vencer y sugerir un descuento. La PO no ha
definido los porcentajes.

## Decision (provisoria)
- Consumo de stock **FEFO**: se vende primero el lote que vence antes.
- Tramos por dias restantes: hasta 3 dias → 30 %; hasta 7 dias → 20 %.
- Dentro de la ventana de aviso del producto pero fuera de los tramos → 10 %.
- Lote vencido: sin descuento (no debe venderse); se marca VENCIDO.
- Ventana de aviso por defecto: 7 dias si el producto no define `dias_aviso`.
- El descuento es **solo una sugerencia**: no cambia el precio del producto ni de la venta.

## Consecuencias
Los tramos viven en `PoliticaDescuento` (`dominio/lotes.py`); cambiarlos no toca el resto
del codigo. Pendiente: confirmar porcentajes y si el descuento debe aplicarse en caja.
