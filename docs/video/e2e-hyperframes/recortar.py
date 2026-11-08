"""Recorta la grabacion E2E usando el registro de clics (clicks.log).

Uso:  python3 recortar.py <carpeta con proxy.mp4 y clicks.log>
Deja en esa carpeta trimmed.mp4, mapa.json y eventos.json.

- proxy.mp4: grabacion a 30 fps ya recortada a la ventana de la app.
- clicks.log: una linea por clic o tecleo: "<tiempo unix> <x> <y> <etiqueta>" (x, y en puntos de pantalla).
- Se descartan los tramos con errores, y las esperas con la pantalla quieta se acortan, salvo las de
  resultado (alertas, estado de cuenta, reportes...), que se dejan el tiempo necesario para leerlas.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

CARPETA = Path(sys.argv[1])
PROXY = CARPETA / "proxy.mp4"
DESFASE = 1.3        # el reloj del registro va adelantado respecto de la grabacion
COLA = 1.5           # lo que se deja despues del ultimo evento
ESPERA_NORMAL = 3.0  # una pantalla quieta se deja este tiempo (despues del cambio)
ANTES_DEL_CLIC = 0.9  # y se vuelve a mostrar un poco antes del siguiente clic (para ver llegar el cursor)
# etiqueta -> segundos que deben verse quietos despues del clic (pantallas de resultado)
RESULTADO = {
    "confirmar-factura": 4.5, "agregar-linea": 4.0, "tab-alertas": 5.8, "merma-observacion": 4.0,
    "registrar-merma": 3.5, "aplicar-descuento": 4.0, "billete-20000": 4.0, "medio-credito": 4.0,
    "abono-monto": 4.0, "tab-estado-cuenta": 8.8, "F6": 6.5, "tab-rentabilidad": 7.5,
    "tab-auditoria": 9.8, "login-entrar-maria": 4.5, "fondo-10000": 3.0,
}


def leer_eventos():
    filas = [l.split() for l in (CARPETA / "clicks.log").read_text().splitlines() if l.strip()]
    t0 = float(filas[0][0])
    ev = []
    for i, f in enumerate(filas):
        ev.append({"i": i, "t": float(f[0]) - t0 - DESFASE * 0 + 0, "x": int(f[1]), "y": int(f[2]), "etq": f[3]})
    return ev, filas


def limpiar(ev):
    """Quita entradas que no fueron clics reales y corrige dos horas registradas antes del clic."""
    por_i = {e["i"]: e for e in ev}
    por_i[4]["t"] = 22.8     # el F7 se registro antes de hacer el clic
    por_i[45]["t"] = 218.2   # idem con el codigo de la merma
    # ingreso fallido (diálogo en otro lugar): entradas 16-20 no sirven
    fuera = {0, 16, 17, 18, 19, 20}
    # el segundo login de Maria es el 13 (entrar): se renombra para proteger su pantalla
    por_i[13]["etq"] = "login-entrar-maria"
    return [e for e in ev if e["i"] not in fuera], (por_i[16]["t"] - 0.4, por_i[21]["t"] - 0.4)


def congelados(fin):
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-t", str(fin), "-i", str(PROXY), "-vf", "freezedetect=n=-55dB:d=1.6",
         "-f", "null", "-"], capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", out)]
    fn = [float(x) for x in re.findall(r"freeze_end: ([0-9.]+)", out)]
    return list(zip(ini, fn))


def main():
    ev, _ = leer_eventos()
    ev, (e_ini, e_fin) = limpiar(ev)
    for e in ev:
        e["rec"] = round(e["t"] + DESFASE, 2)   # tiempo dentro de la grabacion
    fin = ev[-1]["rec"] + COLA
    cortes = [(e_ini + DESFASE, e_fin + DESFASE)]
    for a, b in congelados(fin):
        # el evento que provoco el cambio esta justo antes del comienzo del tramo quieto
        causa = [e for e in ev if a - 2.2 <= e["rec"] <= a + 0.6]
        mantener = max([RESULTADO.get(e["etq"], 0) for e in causa] + [ESPERA_NORMAL])
        if b - a > mantener + ANTES_DEL_CLIC + 0.8:
            cortes.append((a + mantener, b - ANTES_DEL_CLIC))
    # tramos que se conservan
    segs, cur = [], 0.0
    for a, b in sorted(cortes):
        if a > cur:
            segs.append((cur, a))
        cur = max(cur, b)
    segs.append((cur, fin))
    mapa, t, lista = [], 0.0, []
    for i, (a, b) in enumerate(segs):
        if b - a < 0.2:
            continue
        nombre = CARPETA / f"seg{i:03d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(PROXY),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-an", "-r", "30", str(nombre)], check=True)
        lista.append(f"file '{nombre}'")
        mapa.append({"rec_ini": round(a, 3), "rec_fin": round(b, 3), "vid_ini": round(t, 3)})
        t += b - a
    (CARPETA / "lista.txt").write_text("\n".join(lista))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(CARPETA / "lista.txt"),
                    "-c", "copy", str(CARPETA / "trimmed.mp4")], check=True)
    (CARPETA / "mapa.json").write_text(json.dumps({"duracion": round(t, 3), "tramos": mapa}, indent=1))
    (CARPETA / "eventos.json").write_text(json.dumps(ev, indent=1))
    print("duracion:", round(t, 1), "s;", len(mapa), "tramos;", len(ev), "eventos")


main()
