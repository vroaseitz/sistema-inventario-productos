# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para empaquetar la app de escritorio NaturalSur.
#
# IMPORTANTE (ver docs/08-diseno/adr/0001): el .exe hereda la compatibilidad de la
# maquina donde se construye. Para que corra en el Windows 8.1 del local, este spec
# debe compilarse en una VM Windows 8.1 (o Windows 7) con Python 3.11 (64-bit).
# Compilar en Windows 10/11 produce un binario que enlaza DLLs (UCRT / api-ms-win-*)
# ausentes en 8.1 y NO arrancara alli.
#
# Uso (dentro de la VM Win 8.1, con el venv activado):
#   pip install pyinstaller
#   pyinstaller build/pos.spec
# El resultado queda en dist/pos-naturalsur/.

block_cipher = None

a = Analysis(
    ["../src/pos/__main__.py"],
    pathex=["../src"],
    binaries=[],
    datas=[],
    hiddenimports=["psycopg2"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pos-naturalsur",
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="pos-naturalsur",
)
