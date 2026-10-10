# Guía de conexión — VM Windows 8 (Abarrotes / Emporio)

La VM corre en un servidor en AWS con virtualización real (rápida), y solo es accesible por **SSH con llave** — no está expuesta directamente a internet por seguridad (es un Windows 8.1 sin parches desde 2023).

> **Este documento no incluye la IP del servidor ni la contraseña VNC** — esos datos, junto con tu llave SSH individual, te los pasa Fernando por un canal seguro (no por correo/grupo abierto ni por el repositorio, que es público). Reemplaza `<IP_DEL_SERVIDOR>` y `<CONTRASEÑA_VNC>` por los valores reales que recibas.

## Datos del servidor

- **IP del servidor:** `<IP_DEL_SERVIDOR>`
- **Usuario SSH:** `ubuntu`
- **Puerto VNC (dentro del túnel):** `5901`
- **Contraseña VNC:** `<CONTRASEÑA_VNC>`

## Paso 1 — Recibe tu llave privada

Fernando ya generó una llave SSH individual para ti y la agregó al servidor. Te va a mandar un archivo (`eduardo_id_ed25519` o `victoria_id_ed25519`, sin extensión `.pub`) por un canal seguro.

Guárdalo en tu computador, por ejemplo en `~/.ssh/` (Mac/Linux) o `C:\Users\TU_USUARIO\.ssh\` (Windows), y ajústale permisos:

**Mac / Linux:**
```bash
chmod 600 ~/.ssh/tu_nombre_id_ed25519
```

**Windows:** no requiere el `chmod`, pero no lo compartas ni lo subas a ningún repo.

## Paso 2 — Abrir el túnel SSH

**Mac / Linux:**
```bash
ssh -i ~/.ssh/tu_nombre_id_ed25519 -L 5901:localhost:5901 ubuntu@<IP_DEL_SERVIDOR>
```

**Windows (PowerShell):**
```powershell
ssh -i $HOME\.ssh\tu_nombre_id_ed25519 -L 5901:localhost:5901 ubuntu@<IP_DEL_SERVIDOR>
```

Déjalo corriendo (no cierres esa ventana mientras estés conectado a la VM).

## Paso 3 — Conectarte por VNC

Con el túnel abierto, en **otra** ventana de terminal o con un visor VNC:

**Mac:**
```bash
open "vnc://127.0.0.1:5901"
```
Si sale una ventana pidiendo contraseña, ingresa la contraseña VNC que te compartieron por el canal seguro.

> Nota: a veces la app de macOS "Compartir Pantalla" es inestable con esta contraseña (nos pasó). Si falla varias veces, instala un visor VNC alternativo: `brew install --cask vnc-viewer` (RealVNC Viewer) y conéctate a `localhost:5901` ahí.

**Windows:**
Instala un visor VNC gratis, por ejemplo [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/) o TightVNC Viewer. Conéctate a `localhost:5901` con la contraseña VNC que te compartieron.

**Linux:**
```bash
vncviewer localhost:5901
```
(instala con `sudo apt install tigervnc-viewer` si no lo tienes)

## Notas importantes

- La VM y el servidor los dejamos corriendo mientras se estén usando activamente — si van a estar días sin usarla, avisen para apagar la instancia (cuesta ~$0.10 USD/hora encendida).
- **No compartan la contraseña VNC ni la IP fuera del equipo del capstone, y nunca las peguen en este repositorio ni en ningún canal público** — el repo es público y queda en el historial para siempre.
- Si algo no conecta, avisen por el grupo.
