# APEC Profile Updater (Version 2.0)

Application moderne et légère pour automatiser la mise à jour quotidienne de votre profil candidat sur le site de l'**APEC** (apec.fr), afin de maximiser votre visibilité auprès des recruteurs.

---

## 🚀 Améliorations clés par rapport à l'ancienne version

- **Suppression complète de Selenium** : Plus besoin de conteneur Chrome Standalone énergivore tournant H24 avec 2 Go de RAM allouée.
- **Approche Hybride ultra-rapide (API REST + Playwright Stealth)** :
  1. **Niveau 1 (Rapide)** : Le script utilise les cookies de session sauvegardés pour appeler directement l'API interne Apec (`POST /cms/webservices/profilCadre/carteDeVisite`). L'opération prend moins de 1 seconde et ne démarre aucun navigateur.
  2. **Niveau 2 (Renouvellement)** : Uniquement si la session a expiré (HTTP 401/403), un navigateur Chromium headless furtif (**Playwright Stealth**) se lance brièvement (~15 secondes) pour franchir la protection DataDome, s'authentifier et enregistrer les nouveaux cookies.
- **Rotation paramétrable des intitulés de poste** : Variable d'environnement `POSTE_DU_JOUR` supportant plusieurs intitulés séparés par des virgules (ex: alternance automatique jour après jour).
- **Planificateur Cron standard (5 champs)** : Prise en charge des expressions cron standards (ex: `0 8 * * *` pour tous les jours à 08h00, `0 7,19 * * *`, etc.).
- **CI/CD GitHub Actions** : Publication automatique de l'image Docker multi-architecture (`linux/amd64`, `linux/arm64`) sur GitHub Container Registry (`ghcr.io`).

---

## ⚙️ Variables d'environnement

| Variable | Obligatoire | Valeur par défaut | Description |
| :--- | :---: | :--- | :--- |
| `APEC_USERNAME` | **Oui** | - | Votre adresse e-mail de connexion APEC. |
| `APEC_PASSWORD` | **Oui** | - | Votre mot de passe de compte APEC. |
| `POSTE_DU_JOUR` | **Oui** | - | Liste de postes séparés par des virgules (ex: `Ingénieur logiciel, Développeur logiciel`). Erreur levée si absent. |
| `CRON_SCHEDULE` | Non | `0 8 * * *` | Expression cron standard (ex: `0 8 * * *` = chaque jour à 08h00). |
| `RUN_ON_STARTUP` | Non | `true` | Lance immédiatement une mise à jour au démarrage du conteneur. |
| `TZ` | Non | `Europe/Paris` | Fuseau horaire pour le planificateur cron. |
| `LOG_LEVEL` | Non | `INFO` | Niveau de verbosité des logs (`INFO` ou `DEBUG`). |
| `HEADLESS` | Non | `true` | Exécution du navigateur en arrière-plan sans interface graphique. |

---

## 🐳 Déploiement avec Docker Compose (ex: sur votre NAS)

Créez ou utilisez le fichier [docker-compose.yml](file:///home/alex/Projet/UpdateApecProfile/docker-compose.yml) :

```yaml
services:
  updateapecprofile:
    image: ghcr.io/blackbol/update-apec-profile:latest
    container_name: UpdateApecProfile
    restart: unless-stopped
    environment:
      - TZ=Europe/Paris
      - APEC_USERNAME=votre_email@exemple.com
      - APEC_PASSWORD=votre_mot_de_passe
      # Rotation automatique parmi les postes configurés :
      - POSTE_DU_JOUR=Ingénieur logiciel, Développeur logiciel, Lead Développeur
      # Planification cron standard (chaque jour à 08h00) :
      - CRON_SCHEDULE=0 8 * * *
      # Test immédiat au démarrage :
      - RUN_ON_STARTUP=true
      - LOG_LEVEL=INFO
    volumes:
      # Volume pour conserver les cookies de session entre les redémarrages
      - ./data:/app/data
```

### Lancement :

```bash
docker compose up -d
```

### Suivre les logs :

```bash
docker compose logs -f
```

---

## 🍪 Initialisation facile : Import des cookies (Recommandé)

Si vous êtes déjà connecté sur **apec.fr** sur votre navigateur habituel sans aucun anti-bot, vous pouvez transférer vos cookies de session directement dans le projet pour activer immédiatement le **Niveau 1 (API REST ultra-rapide)** sans jamais subir DataDome :

1. Sur votre navigateur personnel, installez l'extension [Cookie-Editor](https://cookie-editor.com/) (Chrome, Firefox, Edge, Brave).
2. Rendez-vous sur votre espace [apec.fr](https://www.apec.fr/) et vérifiez que vous êtes bien connecté.
3. Cliquez sur l'icône de l'extension **Cookie-Editor**, puis sur **Export** > **Export as JSON**.
4. Collez ou enregistrez ce JSON directement dans le fichier `data/cookies.json` du projet.
5. Validez vos cookies immédiatement :
   ```bash
   docker compose run --rm updateapecprofile python -m src.import_cookies
   ```
   > 💡 Une fois importés, vos cookies sont réutilisés et maintenus actifs chaque jour par l'API REST (`curl_cffi`). Le script s'exécute en **0,8 seconde** et aucun navigateur n'a besoin d'être démarré !

---

## 🛠️ Exécution en local (Développement)

1. **Créer un environnement virtuel Python** :
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Créer un fichier `.env`** :
   ```env
   APEC_USERNAME=mon_email@exemple.com
   APEC_PASSWORD=mon_mot_de_passe
   POSTE_DU_JOUR=Ingénieur logiciel, Développeur logiciel
   CRON_SCHEDULE=0 8 * * *
   RUN_ON_STARTUP=true
   DATA_DIR=./data
   ```

3. **Lancer une mise à jour unique** :
   ```bash
   python -m src.main
   ```

4. **Lancer le planificateur cron** :
   ```bash
   python -m src.scheduler
   ```

---

## 📦 Publication de l'image Docker sur GitHub Packages

Le workflow GitHub Actions situé dans [.github/workflows/docker-publish.yml](file:///home/alex/Projet/UpdateApecProfile/.github/workflows/docker-publish.yml) compile automatiquement l'image Docker multi-plateforme (`linux/amd64`, `linux/arm64`) et la pousse vers `ghcr.io` à chaque push sur la branche `main`.
