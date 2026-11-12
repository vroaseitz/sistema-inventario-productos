#!/bin/bash
# Doble clic para abrir la app con la base de la demo (sin Supabase).
cd "$(dirname "$0")/.." || exit 1
[ -f demo/demo.db ] || PYTHONPATH=src .venv/bin/python demo/preparar_demo.py
PYTHONPATH=src POS_SQLITE_PATH="$PWD/demo/demo.db" SUPABASE_DB_URL= exec .venv/bin/python -m pos
