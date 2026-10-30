"""
Outil d'import et de validation des cookies pour UpdateApecProfile.

Permet d'importer les cookies directement depuis votre navigateur personnel
(via l'extension Cookie-Editor ou un fichier JSON exporté) afin de contourner
définitivement tout système anti-bot (DataDome).
"""

import sys
import json
import shutil
from pathlib import Path
from src.config import DATA_DIR, COOKIES_FILE, logger, get_poste_du_jour
from src.apec_api import save_cookies, load_cookies, update_carte_de_visite_via_api


def resolve_file_path(path_str: str) -> Path | None:
    """Tente de trouver le fichier en chemin absolu, relatif, ou dans DATA_DIR."""
    candidates = [
        Path(path_str),
        DATA_DIR / path_str,
        DATA_DIR / Path(path_str).name,
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def sync_cookies_files(target_data: list | dict) -> None:
    """Sauvegarde à la fois dans cookies.json et cookie.json pour compatibilité totale."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_cookies(DATA_DIR / "cookies.json", target_data)
    save_cookies(DATA_DIR / "cookie.json", target_data)


def import_from_json_file(file_path: Path) -> bool:
    """Importe un fichier de cookies JSON exporté depuis un navigateur."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        sync_cookies_files(data)
        logger.info("Cookies importés avec succès depuis %s", file_path)
        return verify_cookies(data)
    except json.JSONDecodeError as e:
        logger.error("Le fichier '%s' ne contient pas un JSON valide : %s", file_path, e)
        return False
    except Exception as e:
        logger.error("Erreur lors de la lecture du fichier '%s' : %s", file_path, e)
        return False


def import_from_text(raw_json_str: str) -> bool:
    """Importe une chaîne JSON de cookies collée directement."""
    raw = raw_json_str.strip()
    if not (raw.startswith("[") or raw.startswith("{")):
        logger.error(
            "Le texte fourni n'est pas un JSON de cookies (ne commence ni par '[' ni par '{'). "
            "Si vous vouliez passer un nom de fichier, vérifiez son chemin."
        )
        return False

    try:
        data = json.loads(raw)
        sync_cookies_files(data)
        logger.info("Cookies enregistrés avec succès dans %s", DATA_DIR / "cookies.json")
        return verify_cookies(data)
    except Exception as e:
        logger.error("Format JSON invalide : %s", e)
        return False


def verify_cookies(data: list | dict) -> bool:
    """Vérifie la présence des cookies essentiels à la session Apec."""
    cookie_names = set()
    if isinstance(data, list):
        for c in data:
            if isinstance(c, dict) and "name" in c:
                cookie_names.add(c["name"])
    elif isinstance(data, dict):
        cookie_names = set(data.keys())

    logger.debug("Cookies détectés : %s", list(cookie_names))

    has_user = "apec.user.cookie" in cookie_names
    has_session = "JSESSIONID" in cookie_names
    has_datadome = "datadome" in cookie_names

    if has_user:
        logger.info("✅ Cookie d'authentification candidat 'apec.user.cookie' présent !")
    else:
        logger.warning("⚠️ Attention : 'apec.user.cookie' n'a pas été trouvé. Assurez-vous d'être bien connecté sur Apec.")

    if has_datadome:
        logger.info("✅ Cookie de sécurité 'datadome' présent.")

    if has_session:
        logger.info("✅ Cookie de session 'JSESSIONID' présent.")

    if has_user and has_datadome:
        logger.info("🎉 Vos cookies sont prêts et enregistrés dans le conteneur !")
        return True
    return False


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        resolved = resolve_file_path(arg)
        if resolved:
            success = import_from_json_file(resolved)
            sys.exit(0 if success else 1)
        elif arg.endswith(".json"):
            logger.error(
                "Fichier introuvable : '%s'. Vérifiez qu'il est bien placé dans le dossier 'data/' de votre projet.",
                arg,
            )
            sys.exit(1)
        else:
            success = import_from_text(arg)
            sys.exit(0 if success else 1)
    else:
        # Recherche automatique dans DATA_DIR
        for candidate_name in ("cookie.json", "cookies.json"):
            candidate = DATA_DIR / candidate_name
            if candidate.exists() and candidate.stat().st_size > 10:
                logger.info("Fichier trouvé automatiquement : %s", candidate)
                success = import_from_json_file(candidate)
                sys.exit(0 if success else 1)

        logger.error("Aucun fichier de cookies trouvé dans %s. Veuillez déposer 'cookie.json'.", DATA_DIR)
        sys.exit(1)


if __name__ == "__main__":
    main()
