#!/bin/bash
# Doble clic para dejar la base de la demo como nueva (borra lo hecho en un ensayo).
cd "$(dirname "$0")/.." || exit 1
PYTHONPATH=src .venv/bin/python demo/preparar_demo.py
echo; read -n 1 -s -r -p "Listo. Presiona una tecla para cerrar."
