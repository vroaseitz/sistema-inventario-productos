# Registro de Decisiones de Arquitectura (ADR)

Los ADR documentan las decisiones técnicas importantes y **por qué** se tomaron, para que
el equipo (y la comisión evaluadora) puedan entenderlas y defenderlas. Formato:
Estado · Contexto · Decisión · Consecuencias.

| # | Decisión | Estado |
|---|---|---|
| [0001](0001-stack-tecnologico.md) | Stack: Python 3.11 + Tkinter + PyInstaller; Supabase vía psycopg2/pooler | Aceptado |
| [0002](0002-operacion-offline.md) | Operación offline: espejo SQLite local + cola de sincronización idempotente | Aceptado |
| [0003](0003-empaquetado-sin-contenedores.md) | Distribución sin contenedores (PyInstaller), no Docker | Aceptado |
