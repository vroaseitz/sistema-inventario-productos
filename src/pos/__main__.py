"""Punto de entrada de la aplicacion de escritorio: la ventana unica (F1 a F7).

La composicion (repositorios, casos de uso, sincronizacion) vive en
`pos.interfaz.ventana_principal.construir_aplicacion`.

Uso:
    python -m pos
"""

from __future__ import annotations


def main() -> None:
    # Import diferido: la GUI (Tkinter) solo se carga al ejecutar, no al importar el
    # paquete, para que los tests del nucleo no dependan de un entorno grafico.
    from pos.interfaz.ventana_principal import main as iniciar

    iniciar()


if __name__ == "__main__":
    main()
