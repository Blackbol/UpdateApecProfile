"""
Outil d'import et de validation des cookies pour UpdateApecProfile.

Permet d'importer les cookies directement depuis votre navigateur personnel
(via l'extension Cookie-Editor ou un fichier JSON exporté) afin de contourner
définitivement tout système anti-bot (DataDome).
"""

import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from curl_cffi import requests
from src.config import DATA_DIR, COOKIES_FILE, logger, get_poste_du_jour
from src.apec_api import save_cookies, load_cookies, update_carte_de_visite_via_api, API_URL, ORIGIN, REFERER


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
    """Vérifie la présence et la validité des cookies essentiels à la session Apec."""
    cookie_dict = {}
    if isinstance(data, list):
        for c in data:
            if isinstance(c, dict) and "name" in c and "value" in c:
                cookie_dict[c["name"]] = str(c["value"])
    elif isinstance(data, dict):
        if "cookies" in data and isinstance(data["cookies"], list):
            for c in data["cookies"]:
                if isinstance(c, dict) and "name" in c and "value" in c:
                    cookie_dict[c["name"]] = str(c["value"])
        else:
            cookie_dict = {k: str(v) for k, v in data.items()}

    cookie_names = set(cookie_dict.keys())
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

    # Vérification de l'horodatage d'expiration d'activité si disponible
    if "apec_activity_cookie_timeout" in cookie_dict:
        try:
            timeout_ms = float(cookie_dict["apec_activity_cookie_timeout"])
            timeout_dt = datetime.fromtimestamp(timeout_ms / 1000)
            if timeout_ms / 1000 < time.time():
                logger.warning(
                    "⚠️ ATTENTION : Le cookie d'activité 'apec_activity_cookie_timeout' indique que la session a expiré le %s !",
                    timeout_dt.strftime("%Y-%m-%d %H:%M:%S"),
                )
            else:
                logger.debug("Horodatage d'activité valide jusqu'au : %s", timeout_dt.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:
            pass

    # Test de validité en direct auprès de l'API Apec
    api_valid = False
    if has_user:
        try:
            session = requests.Session(impersonate="chrome124")
            for k, v in cookie_dict.items():
                session.cookies.set(k, v, domain=".apec.fr", path="/")

            headers = {
                "accept": "application/json, text/plain, */*",
                "origin": ORIGIN,
                "referer": REFERER,
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            }
            res = session.get(API_URL, headers=headers, timeout=10)
            if res.status_code == 200:
                api_valid = True
                logger.info("🎉 Session testée avec succès auprès de l'API Apec (HTTP 200) ! Vos cookies sont actifs et utilisables.")
            elif res.status_code in (400, 401, 403):
                logger.warning(
                    "⚠️ L'API Apec a retourné HTTP %s lors du test direct. "
                    "La session est expirée ou invalidée côté serveur. "
                    "Conseil : reconnectez-vous sur www.apec.fr sur votre navigateur et réexportez vos cookies.",
                    res.status_code,
                )
        except Exception as e:
            logger.debug("Impossible d'effectuer le test API direct : %s", e)

    if has_user and has_datadome:
        if api_valid:
            logger.info("Vos cookies sont prêts et enregistrés avec succès dans le conteneur !")
        else:
            logger.info("Cookies enregistrés. Si la session est expirée, Playwright tentera de renouveler la session automatiquement.")
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
