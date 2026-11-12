"""Adaptadores de impresora. Implementan el puerto `Impresora`.

- `ImpresoraEnArchivo`: guarda cada comprobante como texto en una carpeta. Es lo que se usa mientras
  no haya impresora configurada (y en las pruebas): nada se pierde y se puede revisar.
- `ImpresoraSistema`: manda bytes ESC/POS crudos a la impresora instalada en el equipo (con `lp` en
  macOS/Linux y con pywin32 en Windows). El cajon de dinero se abre con la propia impresora.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from pos.dominio.errores import ErrorImpresion
from pos.infraestructura.impresion.escpos import PULSO_CAJON, a_escpos


class ImpresoraEnArchivo:
    def __init__(self, carpeta: str | Path) -> None:
        self._carpeta = Path(carpeta)
        self.ultimo_archivo: Path | None = None

    def imprimir(self, lineas: list[str], abrir_cajon: bool = False) -> None:
        self._carpeta.mkdir(parents=True, exist_ok=True)
        archivo = self._carpeta / f"comprobante-{datetime.now():%Y%m%d-%H%M%S-%f}.txt"
        texto = "\n".join(lineas)
        if abrir_cajon:
            texto += "\n[se abriria el cajon de dinero]"
        archivo.write_text(texto + "\n", encoding="utf-8")
        self.ultimo_archivo = archivo

    def abrir_cajon(self) -> None:
        """Sin impresora real no hay cajon que abrir."""


class ImpresoraSistema:
    def __init__(self, nombre: str) -> None:
        self._nombre = nombre

    def imprimir(self, lineas: list[str], abrir_cajon: bool = False) -> None:
        self._enviar(a_escpos(lineas, abrir_cajon=abrir_cajon))

    def abrir_cajon(self) -> None:
        self._enviar(PULSO_CAJON)

    def _enviar(self, datos: bytes) -> None:
        try:
            if sys.platform == "win32":
                self._enviar_en_windows(datos)
            else:
                subprocess.run(
                    ["lp", "-d", self._nombre, "-o", "raw"],
                    input=datos,
                    check=True,
                    capture_output=True,
                    timeout=20,
                )
        except ErrorImpresion:
            raise
        except FileNotFoundError as exc:
            raise ErrorImpresion("Este equipo no tiene el comando de impresion (lp)") from exc
        except subprocess.CalledProcessError as exc:
            detalle = exc.stderr.decode(errors="replace").strip() or "la impresora no respondio"
            raise ErrorImpresion(f"No se pudo imprimir en «{self._nombre}»: {detalle}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ErrorImpresion(f"La impresora «{self._nombre}» no respondio a tiempo") from exc

    def _enviar_en_windows(self, datos: bytes) -> None:
        try:
            import win32print  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ErrorImpresion(
                "Falta pywin32 para imprimir en Windows (pip install pywin32)"
            ) from exc
        try:
            manejador = win32print.OpenPrinter(self._nombre)
        except Exception as exc:  # noqa: BLE001 - pywin32 lanza pywintypes.error
            raise ErrorImpresion(f"No se encontro la impresora «{self._nombre}»") from exc
        try:
            win32print.StartDocPrinter(manejador, 1, ("NaturalSur", None, "RAW"))
            win32print.StartPagePrinter(manejador)
            win32print.WritePrinter(manejador, datos)
            win32print.EndPagePrinter(manejador)
            win32print.EndDocPrinter(manejador)
        finally:
            win32print.ClosePrinter(manejador)


def crear_impresora(nombre: str, carpeta: str | Path):
    """Impresora real si hay un nombre configurado; si no, archivos en `carpeta`."""
    nombre = nombre.strip()
    return ImpresoraSistema(nombre) if nombre else ImpresoraEnArchivo(carpeta)
