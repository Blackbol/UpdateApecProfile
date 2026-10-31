#!/bin/bash
set -e

echo "=== Démarrage de l'environnement graphique virtuel ==="

# Nettoyage des verrous X11 résiduels en cas de redémarrage de conteneur
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

# 1. Démarrage de Xvfb (Virtual Framebuffer Display)
export DISPLAY=:99
echo "1. Démarrage de Xvfb sur l'écran :99 (1920x1080)..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset >/dev/null 2>&1 &
XVFB_PID=$!
sleep 1

# 2. Démarrage du gestionnaire de fenêtres léger (Fluxbox)
echo "2. Démarrage de Fluxbox..."
mkdir -p ~/.fluxbox
touch ~/.fluxbox/init
fluxbox >/dev/null 2>&1 &
FLUXBOX_PID=$!
sleep 1

# 3. Démarrage du serveur VNC (x11vnc)
echo "3. Démarrage de x11vnc sur le port 5900..."
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 -quiet >/dev/null 2>&1 &
X11VNC_PID=$!
sleep 1

# 4. Démarrage du proxy Web noVNC (websockify)
echo "4. Démarrage de noVNC sur http://0.0.0.0:6080 ..."
websockify --web /usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &
WEBSOCKIFY_PID=$!
sleep 1

echo "=== noVNC prêt ! Vous pouvez vous connecter sur http://<ip>:6080 ==="

# Fonction de nettoyage lors de l'arrêt
cleanup() {
    echo "Arrêt des services d'affichage..."
    kill $WEBSOCKIFY_PID $X11VNC_PID $FLUXBOX_PID $XVFB_PID 2>/dev/null || true
}
trap cleanup EXIT SIGTERM SIGINT

# Exécute la commande passée (ex: python -m src.scheduler)
exec "$@"
