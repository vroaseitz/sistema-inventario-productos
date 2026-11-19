"""Genera el proyecto HyperFrames del video E2E (guia de 7 escenas).

Uso (desde esta carpeta):  python3 gen.py
Requiere assets/e2e.mp4 (salida de recortar.py), mapa.json y eventos.json.

Con eventos.json se dibujan el cursor (halo y onda de clic), los recuadros verdes sobre lo importante,
los subtitulos que dicen que se esta haciendo y los zooms a los dialogos.
"""

import json
from pathlib import Path

AQUI = Path(__file__).parent
MAPA = json.loads((AQUI / "mapa.json").read_text())
EVENTOS = json.loads((AQUI / "eventos.json").read_text())
POR_I = {e["i"]: e for e in EVENTOS}
DUR = MAPA["duracion"]
INTRO, OUTRO = 4.5, 9.0
TOTAL = round(INTRO + DUR + OUTRO, 2)


def vid(rec: float) -> float:
    """Tiempo de grabacion -> tiempo dentro del recorrido recortado."""
    for t in MAPA["tramos"]:
        if t["rec_ini"] <= rec <= t["rec_fin"]:
            return round(t["vid_ini"] + rec - t["rec_ini"], 2)
        if rec < t["rec_ini"]:
            return round(t["vid_ini"], 2)
    return DUR


def tev(i: int, desp: float = 0.0) -> float:
    """Tiempo (dentro del recorrido) del evento i, mas un desplazamiento en segundos."""
    return round(vid(POR_I[i]["rec"]) + desp, 2)


def a_escenario(x_ss: float, y_ss: float):
    """Coordenadas de una captura de 1000 px de ancho -> coordenadas del escenario (1490x1000)."""
    k = 1.512
    return (x_ss * k - 30) * (1447 / 1326) + 21, (y_ss * k - 66) * (1000 / 916)


def punto(x_pt: float, y_pt: float):
    """Punto de pantalla (el que usan los clics) -> escenario."""
    return (x_pt - 30) * (1447 / 1326) + 21, (y_pt - 66) * (1000 / 916)


def region(x0, y0, x1, y1, tope=2.2):
    ax, ay = a_escenario(x0, y0)
    bx, by = a_escenario(x1, y1)
    w, h = bx - ax, by - ay
    s = max(1.0, min(min(1490 / w, 1000 / h) * 0.92, tope))
    cx, cy = (ax + bx) / 2, (ay + by) / 2
    x = min(0, max(1490 - 1490 * s, 745 - cx * s))
    y = min(0, max(1000 - 1000 * s, 500 - cy * s))
    return round(s, 3), round(x, 1), round(y, 1)


# ---------------- escenas (indice del evento de inicio, nombre, narracion) ----------------
ESCENAS = [
    (1, "Ingreso y vendedora", "María solo ve F1 Operación"),
    (23, "Proveedor y factura", "El costo sube de $7.900 a $8.500"),
    (41, "Stock, alerta y merma", "Alerta de 10 % y merma de 0,1 kg"),
    (51, "Cliente con crédito", "Juan Pérez, cliente familiar"),
    (56, "Venta completa", "Vuelto $15.540 y $7.980 a crédito"),
    (87, "Cuenta y abono", "Total a pagar: $6.384"),
    (94, "Reportes y auditoría", "Margen 29,5 % y 5 cambios auditados"),
]
T = [max(0.0, tev(i, -0.3)) for i, _, _ in ESCENAS] + [DUR]
T[0] = 0.0

# ---------------- subtitulos: evento -> que se esta haciendo ----------------
SUBTITULOS = {
    1: "Entra la administradora con su usuario y contraseña de prueba",
    4: "F7 Administración → Usuarios",
    5: "Nuevo usuario",
    6: "Datos de María González: usuario, contraseña y perfil Vendedora",
    9: "Crear usuario",
    10: "Cerrar sesión para entrar como María",
    11: "María ingresa con su propia cuenta",
    13: "María solo ve F1 Operación: F2 a F7 quedan bloqueados",
    14: "Probar F5: el módulo no se abre",
    15: "Cerrar la sesión de María",
    21: "Vuelve a entrar la administradora",
    23: "F5 Compras",
    24: "Nuevo proveedor",
    25: "Nombre y contacto de Frutos del Sur",
    27: "Crear proveedor",
    28: "Registrar factura de compra",
    29: "Factura 45678: neto $42.500 e IVA $8.075 (total $50.575)",
    32: "Almendras (ALM-GR): 5 kg a $8.500 neto",
    35: "Código de lote L2024-001",
    36: "El vencimiento se elige en el calendario: 30 días desde hoy",
    39: "Agregar línea: la suma ($42.500) cuadra con el neto",
    40: "Confirmar factura: actualiza el costo y suma el stock",
    41: "F3 Inventario",
    42: "Lotes y vencimientos: L2024-001 con 5 kg",
    43: "Alerta: vence en 30 días y sugiere 10 % de descuento ($13.491)",
    44: "Ajustes y mermas",
    45: "Merma de 0,1 kg de Almendras",
    48: "Motivo: Rotura",
    50: "Registrar merma: el stock baja de 5 a 4,9 kg",
    51: "F4 Clientes",
    52: "Nuevo cliente",
    53: "Juan Pérez, con su teléfono de contacto",
    55: "Guardar cliente",
    56: "F1 Operación",
    57: "Pestaña Caja y corte",
    58: "Abrir jornada",
    59: "El fondo se cuenta en billetes: 2 de $20.000 y 1 de $10.000",
    61: "Confirmar: fondo inicial de $50.000",
    62: "Pestaña Venta",
    63: "Venta 1: se escribe el código de las almendras",
    65: "Producto a granel: se ingresa el peso, 0,350 kg",
    67: "Descuento a la línea (F9)",
    69: "Descuento de 15 %",
    71: "El motivo es obligatorio: Cliente frecuente",
    72: "Aplicar: descuento de $787, total a cobrar $4.460",
    73: "Cobrar (F12)",
    74: "Efectivo: entrega $20.000 y el vuelto es $15.540",
    75: "Agregar pago",
    76: "Cobrar solo registrando la venta (F2)",
    78: "Venta 2: se elige a Juan Pérez como cliente",
    80: "Mix de frutos secos, 2 unidades",
    82: "Cobrar (F12)",
    83: "Crédito cliente: $7.980 quedan en la cuenta de Juan",
    84: "Agregar pago",
    85: "Cobrar solo registrando la venta (F2)",
    87: "F4 Clientes",
    88: "Se abre la cuenta de Juan Pérez",
    90: "Registrar abono",
    91: "Abono de $5.000: el saldo baja a $2.980",
    92: "Confirmar abono",
    93: "Estado de cuenta: 20 % de descuento, total a pagar $6.384",
    94: "F6 Reportes: ventas del día",
    95: "Rentabilidad: ganancia de $3.079 y margen de 29,5 %",
    96: "F7 Administración",
    97: "Auditoría: cada cambio queda con su antes y su después",
}

# ---------------- recuadros: (evento, desplazamiento, duracion, region de captura 1000 px) ----------------
RECUADROS = [
    (13, 1.3, 3.8, (100, 106, 578, 125)),      # pestañas bloqueadas para la vendedora
    (39, 0.3, 3.4, (36, 497, 305, 514)),       # suma del detalle y diferencia con el neto
    (40, 0.5, 3.8, (34, 518, 425, 537)),       # factura confirmada
    (43, 0.6, 5.2, (36, 257, 884, 277)),       # fila de la alerta
    (46, 0.9, 5.5, (90, 216, 296, 234)),       # existencia actual y resultante
    (50, 0.5, 3.2, (488, 164, 700, 179)),      # merma registrada
    (55, 0.5, 3.0, (34, 281, 884, 300)),       # cliente guardado con saldo $0
    (61, 0.8, 3.2, (34, 163, 224, 178)),       # turno abierto con fondo inicial
    (72, 0.6, 1.9, (34, 401, 884, 419)),       # linea con descuento
    (72, 2.6, 1.7, (716, 561, 891, 601)),      # total a cobrar
    (74, 0.9, 3.6, (190, 534, 398, 552)),      # pago y vuelto
    (83, 0.9, 3.6, (192, 307, 400, 322)),      # saldo resultante del credito
    (91, 0.9, 3.4, (456, 552, 606, 569)),      # saldo resultante del abono
    (93, 0.6, 7.4, (616, 473, 886, 559)),      # desglose del estado de cuenta
    (94, 0.6, 5.6, (36, 267, 310, 283)),       # resumen de ventas del dia
    (95, 0.6, 3.2, (36, 261, 884, 293)),       # filas de rentabilidad
    (95, 4.0, 3.2, (36, 542, 530, 561)),       # ganancia y margen
    (97, 0.6, 8.6, (34, 257, 886, 351)),       # filas de la auditoria
]

# ---------------- dato clave: etiqueta grande arriba (evento, desp, dur, texto) ----------------
DATOS = [
    (13, 1.3, 3.8, "Solo F1 disponible"),
    (39, 0.3, 3.4, "Diferencia con el neto: $0"),
    (40, 0.5, 3.8, "Costo $7.900 → $8.500"),
    (43, 0.6, 5.2, "Descuento sugerido: 10 %"),
    (50, 0.5, 3.2, "Stock: 5 → 4,9 kg"),
    (55, 0.5, 3.0, "Saldo inicial $0"),
    (61, 0.8, 3.2, "Fondo inicial $50.000"),
    (72, 0.6, 3.6, "Descuento $787 · Total $4.460"),
    (74, 0.9, 3.6, "Vuelto: $15.540"),
    (83, 0.9, 3.6, "A la cuenta de Juan: $7.980"),
    (91, 0.9, 3.4, "Saldo de Juan: $2.980"),
    (93, 0.6, 7.4, "Total a pagar: $6.384"),
    (94, 0.6, 5.6, "2 ventas · $12.440"),
    (95, 4.0, 3.2, "Margen: 29,5 %"),
    (97, 0.6, 8.6, "5 cambios registrados"),
]

# ---------------- zooms: (evento inicio, desp, evento fin, desp, region) ----------------
ZOOMS = [
    (44, 0.9, 50, 0.1, (78, 100, 432, 276)),        # dialogo de merma
    (43, 0.5, 43, 5.4, (440, 238, 885, 285)),       # alerta: saldo, precio, descuento y precio sugerido
    (58, 0.9, 61, 0.1, (268, 290, 460, 607)),       # conteo de billetes del fondo
    (68, 0.7, 72, 0.1, (275, 252, 645, 455)),       # dialogo de descuento
    (73, 0.7, 76, 0.1, (180, 130, 736, 575)),       # cobro en efectivo
    (82, 0.7, 85, 0.1, (180, 130, 736, 525)),       # cobro a credito
    (90, 0.7, 92, 0.1, (402, 424, 638, 610)),       # abono
    (93, 0.6, 93, 7.5, (600, 470, 890, 560)),       # estado de cuenta
    (97, 0.6, 97, 8.6, (270, 240, 885, 345)),       # auditoria
]

# ---------------- index.html ----------------
cam_js = ""
for ia, da, ib, db, r in ZOOMS:
    s, x, y = region(*r)
    ta, tb = INTRO + tev(ia, da), INTRO + tev(ib, db)
    cam_js += f'      tl.to("#cam", {{ scale: {s}, x: {x}, y: {y}, duration: 0.8, ease: "power2.inOut" }}, {round(ta, 2)});\n'
    cam_js += f'      tl.to("#cam", {{ scale: 1, x: 0, y: 0, duration: 0.6, ease: "power2.inOut" }}, {round(tb, 2)});\n'

# cursor: halo que llega a cada clic y onda en el momento del clic
cur_js = "      tl.set('#halo', { x: -200, y: -200, opacity: 0 }, 0);\n"
prev_fin, primero, ult_onda = 0.0, True, -9.0
for e in EVENTOS:
    if e["etq"] in ("FIN",):
        continue
    t = INTRO + tev(e["i"])
    cx, cy = punto(e["x"], e["y"])
    if primero:
        cur_js += f'      tl.set("#halo", {{ x: {cx - 30:.1f}, y: {cy - 30:.1f} }}, {round(max(0, t - 0.7), 2)});\n'
        cur_js += f'      tl.to("#halo", {{ opacity: 1, duration: 0.4 }}, {round(max(0, t - 0.7), 2)});\n'
        primero = False
        prev_fin = round(max(0, t - 0.7) + 0.4, 2)
    else:
        ini = round(max(prev_fin, t - 0.6), 2)
        dur = round(t - ini, 2)
        if dur >= 0.12:
            cur_js += f'      tl.to("#halo", {{ x: {cx - 30:.1f}, y: {cy - 30:.1f}, duration: {dur:.2f}, ease: "power2.inOut" }}, {ini:.2f});\n'
            prev_fin = round(t, 2)
        else:
            cur_js += f'      tl.set("#halo", {{ x: {cx - 30:.1f}, y: {cy - 30:.1f} }}, {max(prev_fin, t):.2f});\n'
            prev_fin = round(max(prev_fin, t), 2)
    if t - ult_onda >= 0.6:
        cur_js += f'      tl.set("#rip", {{ x: {cx - 34:.1f}, y: {cy - 34:.1f} }}, {t:.2f});\n'
        cur_js += f'      tl.fromTo("#rip", {{ scale: 0.3, opacity: 0.95 }}, {{ scale: 1.5, opacity: 0, duration: 0.5, ease: "power2.out", immediateRender: false }}, {t:.2f});\n'
        ult_onda = t

hl_html = hl_js = ""
for k, (i, d, du, r) in enumerate(RECUADROS, 1):
    ax, ay = a_escenario(r[0], r[1])
    bx, by = a_escenario(r[2], r[3])
    ax, ay, bx, by = ax - 7, ay - 5, bx + 7, by + 5
    ta = round(INTRO + tev(i, d), 2)
    hl_html += f'<div id="hl-{k}" class="clip hl" data-start="{ta}" data-duration="{du}" data-track-index="{40 + k}" style="left:{ax:.0f}px;top:{ay:.0f}px;width:{bx - ax:.0f}px;height:{by - ay:.0f}px"></div>'
    hl_js += f'      tl.fromTo("#hl-{k}", {{ opacity: 0, scale: 1.04 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "expo.out" }}, {ta});\n'
    hl_js += f'      tl.fromTo("#hl-{k}", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.3, ease: "power2.in", immediateRender: false }}, {round(ta + du - 0.3, 2)});\n'

dato_html = dato_js = ""
for k, (i, d, du, txt) in enumerate(DATOS, 1):
    ta = round(INTRO + tev(i, d), 2)
    dato_html += f'<div id="dt-{k}" class="clip dato" data-start="{ta}" data-duration="{du}" data-track-index="{70 + k}">{txt}</div>'
    dato_js += f'      tl.fromTo("#dt-{k}", {{ opacity: 0, y: -14, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "expo.out" }}, {ta});\n'
    dato_js += f'      tl.fromTo("#dt-{k}", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.3, ease: "power2.in", immediateRender: false }}, {round(ta + du - 0.3, 2)});\n'

# subtitulos: cada uno dura hasta el siguiente (entre 1,6 y 4,6 s)
claves = sorted(SUBTITULOS, key=lambda i: tev(i))
# si dos subtitulos quedan a menos de 1,5 s, se deja solo el ultimo (el anterior no alcanzaria a leerse)
ok = []
for n, i in enumerate(claves):
    if n + 1 < len(claves) and tev(claves[n + 1]) - tev(i) < 1.8:
        continue
    ok.append(i)
sub_html = sub_js = ""
for n, i in enumerate(ok):
    ini = INTRO + tev(i, -0.15)
    siguiente = INTRO + tev(ok[n + 1], -0.15) if n + 1 < len(ok) else ini + 4.6
    du = round(min(4.8, max(1.5, siguiente - ini - 0.06)), 2)
    sub_html += f'<div id="sb-{n}" class="clip sub" data-start="{ini:.2f}" data-duration="{du}" data-track-index="{100 + n}"><b>{n + 1}/{len(ok)}</b>{SUBTITULOS[i]}</div>'
    sub_js += f'      tl.fromTo("#sb-{n}", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }}, {ini:.2f});\n'
    sub_js += f'      tl.fromTo("#sb-{n}", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.25, ease: "power2.in", immediateRender: false }}, {round(ini + du - 0.25, 2)});\n'

index = f'''<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      :root {{ --ground: #1b2220; --font-display: "Inter", sans-serif; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: var(--ground); }}
      #root {{ position: relative; width: 1920px; height: 1080px; background: var(--ground); font-family: var(--font-display); }}
      #stage {{ position: absolute; left: 20px; top: 40px; width: 1490px; height: 1000px; border-radius: 10px; overflow: hidden; background: #0f1412; }}
      #cam {{ position: absolute; left: 0; top: 0; width: 1490px; height: 1000px; transform-origin: 0 0; }}
      #rec {{ position: absolute; left: 0; top: 0; width: 1490px; height: 1000px; object-fit: cover; }}
      .hl {{ position: absolute; border: 4px solid #7fe3a0; border-radius: 10px; box-shadow: 0 0 0 4000px rgba(5, 9, 7, .38), 0 0 26px rgba(127, 227, 160, .7); }}
      .dato {{ position: absolute; right: 430px; top: 62px; height: 76px; padding: 0 34px; border-radius: 38px; background: #1f7a45; border: 3px solid #bff5d0; color: #ffffff; font-size: 40px; font-weight: 800; line-height: 70px; letter-spacing: -0.01em; white-space: nowrap; z-index: 6; box-shadow: 0 8px 28px rgba(0, 0, 0, .45); }}
      #halo {{ position: absolute; left: 0; top: 0; width: 60px; height: 60px; border-radius: 30px; background: rgba(255, 214, 64, .28); border: 3px solid #ffd640; box-shadow: 0 0 18px rgba(255, 214, 64, .7); opacity: 0; }}
      #rip {{ position: absolute; left: 0; top: 0; width: 68px; height: 68px; border-radius: 34px; border: 4px solid #ffffff; opacity: 0; }}
      .sub {{ position: absolute; left: 56px; top: 952px; height: 76px; padding: 0 34px 0 14px; border-radius: 38px; background: rgba(8, 12, 10, .96); border: 3px solid #7fe3a0; color: #ffffff; font-size: 38px; font-weight: 700; line-height: 70px; white-space: nowrap; z-index: 5; letter-spacing: -0.01em; }}
      .sub b {{ display: inline-block; margin-right: 18px; height: 50px; padding: 0 16px; border-radius: 25px; background: #7fe3a0; color: #0b1a10; font-size: 24px; font-weight: 800; line-height: 50px; vertical-align: middle; position: relative; top: -2px; }}
      .host {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1920" data-height="1080">
      <div id="stage"><div id="cam"><video id="rec" class="clip" src="assets/e2e.mp4" muted playsinline data-start="{INTRO}" data-duration="{DUR}" data-track-index="0"></video>{hl_html}<div id="halo"></div><div id="rip"></div></div></div>
      {dato_html}{sub_html}
      <audio id="musica" class="clip" src="assets/musica.mp3" data-start="0" data-duration="{TOTAL}" data-track-index="9"></audio>
      <div id="panel" class="host" data-composition-id="panel" data-composition-src="compositions/panel.html" data-start="{INTRO}" data-duration="{DUR}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>
      <div id="capitulos" class="host" data-composition-id="capitulos" data-composition-src="compositions/capitulos.html" data-start="{INTRO}" data-duration="{DUR}" data-track-index="2" data-track-kind="graphics" data-width="1920" data-height="1080"></div>
      <div id="intro" class="host" data-composition-id="intro" data-composition-src="compositions/intro.html" data-start="0" data-duration="{INTRO}" data-track-index="3" data-track-kind="graphics" data-width="1920" data-height="1080"></div>
      <div id="outro" class="host" data-composition-id="outro" data-composition-src="compositions/outro.html" data-start="{round(INTRO + DUR, 2)}" data-duration="{OUTRO}" data-track-index="4" data-track-kind="graphics" data-width="1920" data-height="1080"></div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{cam_js}{cur_js}{hl_js}{dato_js}{sub_js}      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
(AQUI / "index.html").write_text(index)

# ---------------- panel ----------------
filas = detalles = js = ""
for i, (_, nombre, narr) in enumerate(ESCENAS, 1):
    a, b = round(T[i - 1], 2), round(T[i], 2)
    top = 190 + (i - 1) * 70
    sal = round(b - 0.3, 2)
    filas += f'''      <div id="pn-row{i}" class="row" style="top:{top}px">
        <div id="pn-hl{i}" class="hl"></div>
        <span class="num">{i}</span><span class="nom">{nombre}</span>
      </div>
'''
    detalles += f'''      <p id="pn-d{i}" class="clip detalle" data-start="{a}" data-duration="{round(b - a, 2)}" data-track-index="2">{narr}</p>
'''
    js += f'''    tl.fromTo("#pn-hl{i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, ease: "power2.out" }}, {a});
    tl.fromTo("#pn-row{i}", {{ opacity: 0.45 }}, {{ opacity: 1, duration: 0.3 }}, {a});
    tl.fromTo("#pn-hl{i}", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.3, immediateRender: false }}, {sal});
    tl.fromTo("#pn-row{i}", {{ opacity: 1 }}, {{ opacity: 0.45, duration: 0.3, immediateRender: false }}, {sal});
    tl.fromTo("#pn-d{i}", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }}, {round(a + 0.2, 2)});
'''
panel = f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #f3f5f4; }}
    #pn-all {{ position: absolute; inset: 0; }}
    #pn-fondo {{ position: absolute; left: 1530px; top: 40px; width: 370px; height: 1000px; background: #232b28; border-radius: 10px; }}
    #pn-titulo {{ position: absolute; left: 1556px; top: 62px; width: 330px; font-size: 32px; font-weight: 800; line-height: 1.1; }}
    #pn-sub {{ position: absolute; left: 1556px; top: 140px; width: 330px; font-size: 20px; color: #b4bdb7; }}
    .row {{ position: absolute; left: 1544px; width: 344px; height: 62px; opacity: 0.5; }}
    .hl {{ position: absolute; inset: 0; background: #2f6b45; border-radius: 10px; opacity: 0; }}
    .num {{ position: absolute; left: 14px; top: 15px; width: 32px; height: 32px; border-radius: 16px; background: #46524d; text-align: center; font-size: 19px; line-height: 32px; font-weight: 800; }}
    .nom {{ position: absolute; left: 62px; top: 14px; font-size: 26px; font-weight: 700; white-space: nowrap; }}
    #pn-prog-fondo {{ position: absolute; left: 1556px; top: 690px; width: 318px; height: 8px; border-radius: 4px; background: #3a4541; }}
    #pn-prog {{ position: absolute; left: 1556px; top: 690px; width: 318px; height: 8px; border-radius: 4px; background: #7fe3a0; transform-origin: left center; }}
    #pn-lbl {{ position: absolute; left: 1556px; top: 722px; font-size: 18px; font-weight: 800; letter-spacing: 0.14em; color: #7fe3a0; }}
    .detalle {{ position: absolute; left: 1556px; top: 760px; width: 322px; font-size: 38px; font-weight: 800; line-height: 1.15; color: #ffffff; letter-spacing: -0.01em; }}
    #pn-nota {{ position: absolute; left: 1556px; top: 968px; width: 322px; font-size: 17px; line-height: 1.3; color: #b4bdb7; }}
  </style>
  <div id="root" data-composition-id="panel" data-width="1920" data-height="1080">
    <div id="pn-all">
      <div id="pn-fondo"></div>
      <h2 id="pn-titulo">Guía E2E en 7 escenas</h2>
      <p id="pn-sub">Emporio NaturalSur · POS e Inventario</p>
{filas}      <div id="pn-prog-fondo"></div>
      <div id="pn-prog"></div>
      <p id="pn-lbl">QUÉ SE COMPRUEBA</p>
{detalles}      <p id="pn-nota">App real con datos de prueba. El círculo amarillo es el cursor.</p>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#pn-all", {{ opacity: 0, x: 40, filter: "blur(8px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.8, ease: "expo.out" }}, 0);
    tl.fromTo("#pn-prog", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {round(DUR - 0.5, 2)}, ease: "none" }}, 0);
{js}    window.__timelines["panel"] = tl;
  </script>
</template>
'''
(AQUI / "compositions").mkdir(exist_ok=True)
(AQUI / "compositions" / "panel.html").write_text(panel)

# ---------------- capitulos ----------------
chips = js2 = ""
for i, (_, nombre, _n) in enumerate(ESCENAS, 1):
    a = round(T[i - 1] + 0.3, 2)
    chips += f'''    <div id="ch-{i}" class="clip chip" data-start="{a}" data-duration="2.4" data-track-index="{2 + i}"><span class="ch-n">ESCENA {i}</span><span class="ch-t">{nombre}</span></div>
'''
    js2 += f'''    tl.fromTo("#ch-{i}", {{ opacity: 0, x: -40, filter: "blur(8px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.5, ease: "expo.out" }}, {a});
    tl.fromTo("#ch-{i}", {{ opacity: 1, x: 0 }}, {{ opacity: 0, x: -20, duration: 0.3, ease: "power2.in", immediateRender: false }}, {round(a + 2.1, 2)});
'''
capitulos = f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #f3f5f4; }}
    .chip {{ position: absolute; left: 56px; top: 68px; height: 60px; padding: 0 26px 0 20px; border-radius: 12px; background: rgba(15,16,22,.92); backdrop-filter: blur(22px); border-left: 6px solid #7fbf95; white-space: nowrap; }}
    .ch-n {{ font-size: 16px; font-weight: 800; letter-spacing: 0.16em; color: #7fbf95; line-height: 60px; margin-right: 16px; }}
    .ch-t {{ font-size: 28px; font-weight: 700; line-height: 60px; }}
  </style>
  <div id="root" data-composition-id="capitulos" data-width="1920" data-height="1080">
{chips}  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{js2}    window.__timelines["capitulos"] = tl;
  </script>
</template>
'''
(AQUI / "compositions" / "capitulos.html").write_text(capitulos)

# ---------------- intro y outro (a partir de los de la demo anterior) ----------------
base = AQUI.parent / "fuente-hyperframes" / "compositions"
intro = (base / "intro.html").read_text()
intro = (
    intro.replace(">Prueba de<", ">Guía E2E<")
    .replace(">punta<", ">en 7<")
    .replace(">a punta<", ">escenas<")
    .replace("Punto de venta e inventario, usado como lo usaría una persona",
             "De la vendedora a la auditoría, con la app real y datos de prueba")
    .replace(">11 pasos<", ">7 escenas<")
    .replace(">Base de prueba<", ">Base nueva<")
    .replace("#in-c2 { left: 330px; } #in-c3 { left: 740px; }", "#in-c2 { left: 350px; } #in-c3 { left: 800px; }")
    .replace("font-size: 22px; font-weight: 700; letter-spacing: 0.22em", "font-size: 28px; font-weight: 700; letter-spacing: 0.22em")
)
(AQUI / "compositions" / "intro.html").write_text(intro)

outro = (base / "outro.html").read_text()
outro = (
    outro.replace(">Resultado de la prueba<", ">Resultado del recorrido<")
    .replace('<div class="cifra">11</div><div class="rotulo">pasos recorridos con la app real: de abrir la jornada al corte</div>',
             '<div class="cifra">7</div><div class="rotulo">escenas recorridas con la app real, sin errores ni datos cargados a mano</div>')
    .replace('<div class="cifra">$0</div><div class="rotulo">de diferencia en el corte: esperado $21.350, contado $21.350</div>',
             '<div class="cifra">$2.980</div><div class="rotulo">saldo final de Juan Pérez: consumo $7.980, abono $5.000, 20 % descontado</div>')
    .replace('<div class="cifra">6</div><div class="rotulo">problemas encontrados en la prueba y ya corregidos</div>',
             '<div class="cifra">5</div><div class="rotulo">cambios quedaron en la auditoría con su antes y después</div>')
    .replace(
        "<b>Pendiente:</b> aplicar la migración 007 en Supabase, sincronizar clientes, compras y proveedores, y probar la impresora real.",
        "<b>Diferencias con la guía original:</b> la app no pide RUT, y en productos perecibles el lote y el vencimiento son obligatorios. "
        "<b>Pendiente:</b> probar con impresora real.",
    )
)
(AQUI / "compositions" / "outro.html").write_text(outro)

for nombre in ("hyperframes.json", "meta.json", "package.json"):
    (AQUI / nombre).write_text((AQUI.parent / "fuente-hyperframes" / nombre).read_text())
print("proyecto generado:", TOTAL, "s en total; escenas en", [round(t, 1) for t in T])
