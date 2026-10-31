import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from croniter import croniter

# Charge les variables du fichier .env si la dépendance est présente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration du logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("UpdateApecProfile")

# Identifiants APEC
APEC_USERNAME = os.getenv("APEC_USERNAME", "").strip()
APEC_PASSWORD = os.getenv("APEC_PASSWORD", "").strip()

# Variable obligatoire pour la rotation des postes
POSTE_DU_JOUR_RAW = os.getenv("POSTE_DU_JOUR", "").strip()

# Paramètres de persistance et de planification
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))


def find_cookies_file() -> Path:
    """Recherche le fichier de cookies existant (cookies.json ou cookie.json)."""
    for filename in ("cookies.json", "cookie.json"):
        candidate = DATA_DIR / filename
        if candidate.exists() and candidate.stat().st_size > 10:
            return candidate
    return DATA_DIR / "cookies.json"


COOKIES_FILE = find_cookies_file()
CRON_SCHEDULE_RAW = os.getenv("CRON_SCHEDULE") or os.getenv("SCHEDULE_TIME", "0 8 * * *").strip()
RUN_ON_STARTUP = os.getenv("RUN_ON_STARTUP", "true").lower() in ("true", "1", "yes")
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes")


def validate_config() -> None:
    """Valide la présence des variables d'environnement obligatoires."""
    errors = []
    if not APEC_USERNAME:
        errors.append("La variable d'environnement 'APEC_USERNAME' est obligatoire.")
    if not APEC_PASSWORD:
        errors.append("La variable d'environnement 'APEC_PASSWORD' est obligatoire.")
    if not POSTE_DU_JOUR_RAW:
        errors.append(
            "La variable d'environnement 'POSTE_DU_JOUR' est obligatoire. "
            "Exemple : POSTE_DU_JOUR=\"Ingénieur logiciel, Développeur logiciel, Lead Dev\""
        )

    # Validation du cronjob
    try:
        get_cron_expression()
    except ValueError as e:
        errors.append(str(e))

    if errors:
        for err in errors:
            logger.error(err)
        raise ValueError("\n".join(errors))


def get_postes_list() -> list[str]:
    """Extrait et nettoie la liste des postes configurés."""
    if not POSTE_DU_JOUR_RAW:
        raise ValueError("POSTE_DU_JOUR n'est pas défini ou est vide.")

    postes = [p.strip() for p in POSTE_DU_JOUR_RAW.split(",") if p.strip()]
    if not postes:
        raise ValueError("Aucun poste valide trouvé dans POSTE_DU_JOUR.")
    return postes


def get_poste_du_jour() -> str:
    """
    Sélectionne le poste du jour de manière déterministe en alternant
    chaque jour parmi la liste fournie.
    """
    postes = get_postes_list()
    # Utilise le jour de l'année (1 à 366) pour alterner chaque jour
    day_index = datetime.now().timetuple().tm_yday % len(postes)
    poste = postes[day_index]
    logger.info("Poste du jour sélectionné : '%s' (index %d/%d)", poste, day_index + 1, len(postes))
    return poste


def get_cron_expression() -> str:
    """
    Récupère et valide l'expression cron standard (ex: '0 8 * * *').
    Prend également en charge la conversion automatique si un format 'HH:MM' est fourni.
    """
    expr = CRON_SCHEDULE_RAW

    # Support de courtoisie si format HH:MM
    if ":" in expr and len(expr.split(":")) == 2:
        parts = expr.split(":")
        try:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                expr = f"{m} {h} * * *"
        except ValueError:
            pass

    if not croniter.is_valid(expr):
        raise ValueError(
            f"Format cronjob invalide : '{CRON_SCHEDULE_RAW}'. "
            "Veuillez fournir une expression cron standard à 5 champs (ex: '0 8 * * *')."
        )
    return expr
