"""Tema visual de NaturalSur: colores, tipografia y estilos ttk tomados del prototipo v3.

Los valores salen de las variables CSS del prototipo (`--ink`, `--line`, `--fill`, `--brand`) y de
los colores por modulo (`MOD`). Se usa el tema «clam» de ttk porque es el unico que respeta los
colores en macOS, Windows y Linux por igual: con el tema nativo cada sistema pinta distinto.
"""

from __future__ import annotations

import contextlib
import re
import tkinter as tk
from tkinter import ttk

TINTA = "#1b2220"
TINTA_2 = "#5a6560"
TINTA_3 = "#8c958f"
LINEA = "#c8cecb"
LINEA_2 = "#e4e8e6"
RELLENO = "#f3f5f4"
PAPEL = "#ffffff"
MARCA = "#2f6b45"
PELIGRO = "#9d3b2f"
ALERTA_FONDO = "#fbeee9"  # fila que pide atencion (agotado, bajo el minimo, sin costo)
CABECERA = "#23292a"

# Color del modulo y su version clara (la que pinta la fila de acciones y la seleccion).
MODULOS_COLOR = {
    "F1": ("#1D4E6F", "#E8F0F5"),
    "F2": ("#8A5A17", "#F7F0E3"),
    "F3": ("#5B3E7E", "#F0EBF6"),
    "F4": ("#2E6B3E", "#E9F2EA"),
    "F5": ("#7A4A2E", "#F5EEE9"),
    "F6": ("#1E5F63", "#E7F1F1"),
    "F7": ("#4A4F55", "#EEEFF0"),
}


def fuente(tamano: int = 11, negrita: bool = False) -> tuple:
    return ("TkDefaultFont", tamano, "bold") if negrita else ("TkDefaultFont", tamano)


def centrar(ventana: tk.Misc, referencia: tk.Misc | None = None) -> None:
    """Pone un cuadro modal centrado sobre la ventana y siempre dentro de la pantalla."""
    ventana.update_idletasks()
    ancho, alto = ventana.winfo_reqwidth(), ventana.winfo_reqheight()
    pantalla_x, pantalla_y = ventana.winfo_screenwidth(), ventana.winfo_screenheight()
    if referencia is not None:
        x = referencia.winfo_rootx() + (referencia.winfo_width() - ancho) // 2
        y = referencia.winfo_rooty() + (referencia.winfo_height() - alto) // 2
    else:
        x, y = (pantalla_x - ancho) // 2, (pantalla_y - alto) // 2
    x = max(0, min(x, pantalla_x - ancho))
    y = max(30, min(y, pantalla_y - alto - 60))
    ventana.geometry(f"+{x}+{y}")


_NUMERICO = re.compile(r"^[\s$]*[\d.,]+\s*%?$")


def _seleccionar_si_es_numero(evento: tk.Event) -> None:
    """R-03: al entrar a un campo con un numero (p. ej. el 0 de la meta), queda seleccionado: lo
    que se escribe lo reemplaza en vez de quedar pegado detras del 0."""
    campo = evento.widget
    with contextlib.suppress(tk.TclError, AttributeError):
        if _NUMERICO.match(campo.get()):
            campo.after_idle(lambda: campo.select_range(0, "end"))


def aplicar_tema(raiz: tk.Misc) -> ttk.Style:
    """Deja los widgets ttk con el aspecto del prototipo. Se llama una vez al abrir la ventana."""
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    raiz.bind_class("TEntry", "<FocusIn>", _seleccionar_si_es_numero, add="+")
    raiz.bind_class("Entry", "<FocusIn>", _seleccionar_si_es_numero, add="+")
    raiz.configure(bg=PAPEL)
    raiz.option_add("*Toplevel.background", PAPEL)  # cuadros de dialogo: fondo claro siempre
    # Widgets tk "crudos": sin esto toman los colores del modo oscuro del sistema (texto blanco).
    raiz.option_add("*Label.foreground", TINTA)
    raiz.option_add("*Entry.background", PAPEL)
    raiz.option_add("*Entry.foreground", TINTA)
    raiz.option_add("*Entry.insertBackground", TINTA)
    raiz.option_add("*Entry.disabledBackground", RELLENO)
    raiz.option_add("*Entry.disabledForeground", TINTA_3)
    raiz.option_add("*Entry.highlightBackground", LINEA)
    raiz.option_add("*Entry.highlightColor", MARCA)
    raiz.option_add("*Text.background", PAPEL)
    raiz.option_add("*Text.foreground", TINTA)
    raiz.option_add("*Listbox.background", PAPEL)
    raiz.option_add("*Listbox.foreground", TINTA)
    raiz.option_add("*Listbox.highlightColor", LINEA)
    raiz.option_add("*TCombobox*Listbox.background", PAPEL)
    raiz.option_add("*TCombobox*Listbox.foreground", TINTA)

    estilo.configure(".", background=PAPEL, foreground=TINTA, font=fuente(), bordercolor=LINEA)
    estilo.configure("TFrame", background=PAPEL)
    estilo.configure("TLabel", background=PAPEL, foreground=TINTA)
    estilo.configure("TLabelframe", background=PAPEL, bordercolor=LINEA_2, relief="solid")
    estilo.configure(
        "TLabelframe.Label", background=PAPEL, foreground=TINTA_2, font=fuente(10, True)
    )

    estilo.configure(
        "TButton",
        background=PAPEL,
        foreground=TINTA,
        bordercolor=LINEA,
        lightcolor=PAPEL,
        darkcolor=PAPEL,
        relief="solid",
        borderwidth=1,
        padding=(11, 5),
        focuscolor=PAPEL,
    )
    estilo.map(
        "TButton",
        background=[("pressed", LINEA_2), ("active", RELLENO)],
        bordercolor=[("active", TINTA_3)],
    )
    estilo.configure("Peligro.TButton", foreground=PELIGRO, bordercolor="#d9b4ad", background=PAPEL)
    estilo.configure(
        "Primario.TButton",
        background=MODULOS_COLOR["F1"][0],
        foreground="#ffffff",
        bordercolor=MODULOS_COLOR["F1"][0],
        lightcolor=MODULOS_COLOR["F1"][0],
        darkcolor=MODULOS_COLOR["F1"][0],
        font=fuente(11, True),
    )
    estilo.map("Primario.TButton", background=[("active", TINTA)], foreground=[("active", PAPEL)])

    estilo.configure(
        "TEntry",
        fieldbackground=PAPEL,
        bordercolor=LINEA,
        lightcolor=LINEA,
        darkcolor=LINEA,
        padding=5,
    )
    estilo.map("TEntry", bordercolor=[("focus", MODULOS_COLOR["F1"][0])])
    estilo.configure(
        "TCombobox",
        fieldbackground=PAPEL,
        background=PAPEL,
        bordercolor=LINEA,
        arrowcolor=TINTA_2,
        padding=4,
    )
    estilo.map("TCombobox", fieldbackground=[("readonly", PAPEL)], bordercolor=[("focus", TINTA_2)])
    estilo.configure("TCheckbutton", background=PAPEL)
    estilo.configure("TSeparator", background=LINEA_2)

    # Tablas: cabecera gris suave con texto pequeno, filas de 26 px y seleccion con el tinte del
    # modulo.
    estilo.configure(
        "Treeview",
        background=PAPEL,
        fieldbackground=PAPEL,
        foreground=TINTA,
        bordercolor=LINEA,
        rowheight=26,
        borderwidth=1,
        relief="solid",
    )
    estilo.map(
        "Treeview",
        background=[("selected", MODULOS_COLOR["F1"][1])],
        foreground=[("selected", TINTA)],
    )
    estilo.configure(
        "Treeview.Heading",
        background=RELLENO,
        foreground=TINTA_2,
        font=fuente(10, True),
        relief="flat",
        padding=(6, 6),
        bordercolor=LINEA,
    )
    estilo.map("Treeview.Heading", background=[("active", LINEA_2)])

    # Sub-pestanas como «pildoras» (Venta · Caja y corte · Resumen del dia).
    estilo.configure("TNotebook", background=PAPEL, borderwidth=0, tabmargins=(0, 6, 0, 0))
    estilo.configure(
        "TNotebook.Tab",
        background=PAPEL,
        foreground=TINTA,
        bordercolor=LINEA,
        padding=(12, 5),
        font=fuente(11),
    )
    estilo.map(
        "TNotebook.Tab",
        background=[("selected", MODULOS_COLOR["F1"][0]), ("active", RELLENO)],
        foreground=[("selected", "#ffffff")],
        bordercolor=[("selected", MODULOS_COLOR["F1"][0])],
    )
    estilo.configure("TScrollbar", background=LINEA_2, troughcolor=RELLENO, bordercolor=LINEA_2)
    return estilo


def colorear_modulo(estilo: ttk.Style, clave: str) -> None:
    """Pinta lo que cambia con el modulo: pildora activa, seleccion de tabla y boton primario."""
    color, claro = MODULOS_COLOR[clave]
    estilo.map(
        "TNotebook.Tab",
        background=[("selected", color), ("active", RELLENO)],
        foreground=[("selected", "#ffffff")],
        bordercolor=[("selected", color)],
    )
    estilo.map("Treeview", background=[("selected", claro)], foreground=[("selected", TINTA)])
    estilo.configure(
        "Primario.TButton",
        background=color,
        bordercolor=color,
        lightcolor=color,
        darkcolor=color,
    )
    estilo.map("TEntry", bordercolor=[("focus", color)])


class BotonAccion(tk.Frame):
    """Boton del prototipo: una insignia con la tecla (F10, INS, DEL...) y el texto al lado.

    `variante`: «normal» (borde gris), «peligro» (texto rojo) o «primario» (color del modulo).
    """

    def __init__(
        self,
        parent: tk.Misc,
        texto: str,
        comando,
        tecla: str = "",
        variante: str = "normal",
        color: str = "#1D4E6F",
        fondo: str = PAPEL,
    ) -> None:
        primario = variante == "primario"
        super().__init__(
            parent,
            bg=color if primario else fondo,
            highlightthickness=1,
            highlightbackground=color if primario else LINEA,
            cursor="hand2",
        )
        self._comando = comando
        self._normal = color if primario else fondo
        self._hover = TINTA if primario else RELLENO
        texto_color = "#ffffff" if primario else (PELIGRO if variante == "peligro" else TINTA)
        self._piezas = []
        if tecla:
            insignia = tk.Label(
                self,
                text=tecla,
                bg="#3a6786" if primario else "#dfe4e2",
                fg="#ffffff" if primario else TINTA_2,
                font=fuente(9),
                padx=4,
            )
            insignia.pack(side="left", padx=(5, 3), pady=5)
            self._piezas.append(insignia)
        etiqueta = tk.Label(
            self,
            text=texto,
            bg=self._normal,
            fg=texto_color,
            font=fuente(10, primario),
            padx=0 if tecla else 8,
        )
        etiqueta.pack(side="left", padx=(0, 7), pady=5)
        self._etiqueta = etiqueta
        for pieza in (self, etiqueta, *self._piezas):
            pieza.bind("<Button-1>", lambda _e: self.invoke())
            pieza.bind("<Enter>", lambda _e: self._pintar(self._hover))
            pieza.bind("<Leave>", lambda _e: self._pintar(self._normal))

    def _pintar(self, fondo: str) -> None:
        self.config(bg=fondo)
        self._etiqueta.config(bg=fondo)

    def invoke(self) -> None:
        self._comando()
