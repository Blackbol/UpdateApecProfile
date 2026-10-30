import sys
from src.config import (
    validate_config,
    get_poste_du_jour,
    COOKIES_FILE,
    logger,
)
from src.apec_api import load_cookies, update_carte_de_visite_via_api
from src.playwright_auth import authenticate_and_update


def run() -> bool:
    """
    Exécute le processus complet de mise à jour du profil :
    1. Validation des variables d'environnement.
    2. Sélection du poste du jour.
    3. Tentative d'appel API direct si les cookies sont en cache.
    4. En cas d'échec ou d'absence de cookies, reconnexion via Playwright furtif.
    """
    logger.info("=== Début du rafraîchissement du profil APEC ===")

    try:
        validate_config()
    except ValueError as e:
        logger.error("Erreur de configuration : %s", e)
        return False

    poste_du_jour = get_poste_du_jour()

    # Étape 1 : Essai avec les cookies déjà enregistrés
    if COOKIES_FILE.exists():
        logger.debug("Fichier de cookies trouvé (%s). Tentative d'appel direct...", COOKIES_FILE)
        cookies = load_cookies(COOKIES_FILE)
        success, message = update_carte_de_visite_via_api(cookies, poste_du_jour)

        if success:
            logger.info("SUCCÈS : %s", message)
            logger.info("=== Fin du rafraîchissement (sans lancement de navigateur) ===")
            return True

        logger.debug("Appel direct non concluant : %s", message)
        logger.info("Mise à jour via le navigateur...")
    else:
        logger.info("Aucun cookie enregistré. Premier lancement via le navigateur...")

    # Étape 2 : Reconnexion et mise à jour via Playwright
    success, message = authenticate_and_update(poste_du_jour, COOKIES_FILE)

    if success:
        logger.info("SUCCÈS : %s", message)
        logger.info("=== Fin du rafraîchissement (session renouvelée) ===")
        return True
    else:
        logger.error("ÉCHEC : %s", message)
        return False


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
