import json
import time
from pathlib import Path
from typing import Tuple
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

from src.config import (
    APEC_USERNAME,
    APEC_PASSWORD,
    HEADLESS,
    logger,
)
from src.apec_api import save_cookies, API_URL

TARGET_URL = "https://www.apec.fr/candidat/mon-espace/profil.html/carte-visite"


def dismiss_cookie_banner(page: Page) -> None:
    """Ferme la bannière de consentement des cookies si elle s'affiche."""
    selectors = [
        "#didomi-notice-agree-button",
        "#didomi-notice-disagree-button",
        "button:has-text('Continuer sans accepter')",
        "button:has-text('Tout refuser')",
        "button:has-text('Refuser')",
        "button:has-text('Accepter')",
        "button:has-text('Tout accepter')",
    ]
    for selector in selectors:
        try:
            elem = page.locator(selector).first
            if elem.is_visible(timeout=1500):
                elem.click()
                logger.info("Bannière de cookies fermée via le sélecteur: %s", selector)
                time.sleep(1)
                break
        except Exception:
            continue


def authenticate_and_update(nouveau_poste: str, cookies_path: Path) -> Tuple[bool, str]:
    """
    Lance un navigateur Playwright avec mode furtif (stealth) pour :
    1. Résoudre le challenge anti-bot DataDome.
    2. S'authentifier sur l'Apec avec login/mot de passe.
    3. Sauvegarder les nouveaux cookies dans un fichier.
    4. Mettre à jour le poste sur la carte de visite via l'API interne du navigateur.

    Retourne : (succès: bool, message: str)
    """
    logger.info("Démarrage du navigateur Playwright (mode furtif, headless=%s)...", HEADLESS)

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--window-size=1920,1080",
            ],
        )

        context: BrowserContext = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )

        # Applique les techniques d'évasion stealth
        stealth = Stealth()
        stealth.apply_stealth_sync(context)

        page: Page = context.new_page()

        try:
            logger.info("Navigation vers %s ...", TARGET_URL)
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)

            dismiss_cookie_banner(page)

            # Recherche des champs de connexion
            email_selectors = [
                "input[type='email']",
                "input[name='username']",
                "input[name='email']",
                "input#email",
                "input[formcontrolname='username']",
            ]
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input#password",
                "input[formcontrolname='password']",
            ]
            submit_selectors = [
                "button[type='submit']",
                "button:has-text('Se connecter')",
                "button:has-text('Connexion')",
            ]

            email_field = None
            for sel in email_selectors:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    email_field = loc
                    break

            if email_field:
                logger.info("Formulaire de connexion détecté. Renseignement des identifiants...")
                email_field.fill(APEC_USERNAME)
                time.sleep(0.5)

                for sel in password_selectors:
                    pwd_loc = page.locator(sel).first
                    if pwd_loc.is_visible(timeout=2000):
                        pwd_loc.fill(APEC_PASSWORD)
                        break

                time.sleep(0.5)
                for sel in submit_selectors:
                    sub_loc = page.locator(sel).first
                    if sub_loc.is_visible(timeout=2000):
                        sub_loc.click()
                        break

                logger.info("Validation du formulaire de connexion envoyée. En attente de la session...")
                # Attente que la redirection ou la session s'établisse
                try:
                    page.wait_for_url("**/mon-espace/**", timeout=30000)
                except Exception:
                    # Parfois l'URL reste la même ou la SPA se charge dynamiquement
                    time.sleep(5)

            # Vérification des cookies acquis
            cookies = context.cookies()
            cookie_names = [c["name"] for c in cookies]
            logger.info("Cookies obtenus via Playwright : %s", cookie_names)

            if "apec.user.cookie" not in cookie_names and "JSESSIONID" not in cookie_names:
                logger.warning(
                    "Les cookies de session utilisateur n'ont pas été trouvés. "
                    "Vérifiez vos identifiants ou si un CAPTCHA supplémentaire est actif."
                )

            # Sauvegarde des cookies pour les prochains runs
            save_cookies(cookies_path, cookies)
            logger.info("Nouveaux cookies sauvegardés dans %s", cookies_path)

            # Mise à jour du profil via le contexte authentifié
            logger.info("Récupération du profil actuel via l'API interne du navigateur...")
            get_res = context.request.get(API_URL, headers={"accept": "application/json, text/plain, */*"})

            if get_res.status != 200:
                return (
                    False,
                    f"Échec de la récupération du profil après connexion (HTTP {get_res.status}) : {get_res.text()[:200]}",
                )

            profile_data = get_res.json()
            ancien_poste = profile_data.get("metierSouhaite", "")
            logger.info("Poste actuel sur l'Apec : '%s' -> Nouveau poste : '%s'", ancien_poste, nouveau_poste)

            profile_data["metierSouhaite"] = nouveau_poste

            logger.info("Envoi de la mise à jour via POST carteDeVisite...")
            post_res = context.request.post(
                API_URL,
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/plain, */*",
                    "origin": "https://www.apec.fr",
                    "referer": TARGET_URL,
                },
                data=json.dumps(profile_data),
            )

            if post_res.status in (200, 204):
                return (
                    True,
                    f"Profil Apec mis à jour avec succès après ré-authentification Playwright ! (HTTP {post_res.status})",
                )
            else:
                return (
                    False,
                    f"Échec de la mise à jour via Playwright (HTTP {post_res.status}) : {post_res.text()[:200]}",
                )

        except Exception as e:
            logger.error("Erreur durant l'exécution Playwright : %s", e)
            return False, f"Erreur Playwright : {e}"

        finally:
            context.close()
            browser.close()
            logger.info("Navigateur Playwright fermé.")
