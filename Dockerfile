# Image officielle Playwright Python contenant Chromium et toutes les dépendances système requises
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY src/ ./src/

# Création du répertoire de persistance pour les cookies
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data

VOLUME ["/app/data"]

# Lance le scheduler par défaut
CMD ["python", "-m", "src.scheduler"]
