# Image officielle Playwright Python contenant Chromium et toutes les dépendances système requises
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Paris

# Installation de Xvfb, x11vnc, noVNC, fluxbox et websockify pour l'accès visuel direct via navigateur web
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    fluxbox \
    net-tools \
    tzdata \
    && ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime \
    && echo "Europe/Paris" > /etc/timezone \
    && ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du script d'entrée graphique noVNC
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copie du code source
COPY src/ ./src/

# Création du répertoire de persistance pour les cookies
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV DISPLAY=:99

# Port noVNC (accessible via http://<ip>:6080)
EXPOSE 6080

VOLUME ["/app/data"]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "src.scheduler"]
