import json
from pathlib import Path
from typing import Optional, Tuple
from curl_cffi import requests
from src.config import logger

API_URL = "https://www.apec.fr/cms/webservices/profilCadre/carteDeVisite"
REFERER = "https://www.apec.fr/candidat/mon-espace/profil.html/carte-visite"
ORIGIN = "https://www.apec.fr"


def load_cookies(cookies_path: Path) -> dict[str, str]:
    """
    Charge les cookies depuis un fichier JSON.
    Prend en charge le format Playwright (liste de dicts) ou un dictionnaire direct.
    """
    if not cookies_path.exists():
        return {}

    try:
        with open(cookies_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies_dict = {}
        if isinstance(data, list):
            # Format exporté par Playwright: [{'name': '...', 'value': '...'}, ...]
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies_dict[item["name"]] = item["value"]
        elif isinstance(data, dict):
            # Format direct {nom: valeur} ou {cookies: [...]}
            if "cookies" in data and isinstance(data["cookies"], list):
                for item in data["cookies"]:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        cookies_dict[item["name"]] = item["value"]
            else:
                cookies_dict = data

        return cookies_dict
    except Exception as e:
        logger.warning("Impossible de lire le fichier de cookies '%s' : %s", cookies_path, e)
        return {}


def save_cookies(cookies_path: Path, cookies: list[dict] | dict) -> None:
    """Sauvegarde les cookies dans un fichier JSON."""
    cookies_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cookies_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)
    logger.debug("Cookies sauvegardés dans %s", cookies_path)


def update_carte_de_visite_via_api(cookies: dict[str, str], nouveau_poste: str) -> Tuple[bool, str]:
    """
    Tente de mettre à jour la carte de visite Apec directement via l'API REST
    avec curl_cffi en usurpant l'empreinte TLS d'un navigateur Chrome moderne.

    Retourne : (succès: bool, message: str)
    """
    if not cookies:
        return False, "Aucun cookie disponible."

    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": ORIGIN,
        "referer": REFERER,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    try:
        session = requests.Session(impersonate="chrome124")
        session.cookies.update(cookies)

        logger.info("Tentative de récupération du profil existant via l'API...")
        get_response = session.get(API_URL, headers=headers, timeout=15)

        if get_response.status_code != 200:
            return (
                False,
                f"Échec de la récupération du profil (HTTP {get_response.status_code}). Session probablement expirée.",
            )

        try:
            profile_data = get_response.json()
        except Exception:
            return False, "La réponse reçue n'est pas du JSON valide (redirection ou challenge anti-bot)."

        if not isinstance(profile_data, dict) or "idProfilCadre" not in profile_data:
            return False, "Le JSON récupéré ne contient pas le profil candidat attendu."

        ancien_poste = profile_data.get("metierSouhaite", "")
        logger.info("Poste actuel sur l'Apec : '%s' -> Nouveau poste : '%s'", ancien_poste, nouveau_poste)

        # Mise à jour du métier souhaité
        profile_data["metierSouhaite"] = nouveau_poste

        # Envoi de la mise à jour (POST)
        headers["content-type"] = "application/json"
        logger.info("Envoi de la mise à jour de la carte de visite...")
        post_response = session.post(
            API_URL,
            headers=headers,
            data=json.dumps(profile_data),
            timeout=15,
        )

        if post_response.status_code in (200, 204):
            return True, f"Profil Apec mis à jour avec succès via l'API REST ! (HTTP {post_response.status_code})"
        else:
            return (
                False,
                f"Échec de la mise à jour via POST (HTTP {post_response.status_code}) : {post_response.text[:200]}",
            )

    except Exception as e:
        return False, f"Erreur lors de la requête API directe : {e}"
