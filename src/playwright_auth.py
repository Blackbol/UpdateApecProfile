import json
import time
import random
from pathlib import Path
from typing import Tuple, Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page

from src.config import (
    APEC_USERNAME,
    APEC_PASSWORD,
    HEADLESS,
    DATA_DIR,
    LOG_LEVEL,
    logger,
)
from src.apec_api import save_cookies, API_URL

TARGET_URL = "https://www.apec.fr/candidat/mon-espace/profil.html/carte-visite"
LOGIN_URL = "https://www.apec.fr/candidat/connexion.html"


def dismiss_cookie_banner(page: Page) -> bool:
    """Ferme la bannière de consentement des cookies si elle s'affiche."""
    selectors = [
        "xpath=/html/body/div[1]/div/div/div/div/div/div[3]/button[2]",
        "#didomi-notice-agree-button",
        "#didomi-notice-disagree-button",
        "button[id*='didomi']",
        "button:has-text('Continuer sans accepter')",
        "button:has-text('Tout refuser')",
        "button:has-text('Refuser')",
        "button:has-text('Accepter')",
        "button:has-text('Tout accepter')",
    ]
    for selector in selectors:
        try:
            elem = page.locator(selector).first
            if elem.is_visible(timeout=1000):
                elem.click()
                logger.debug("Bannière de cookies fermée via: %s", selector)
                time.sleep(0.5)
                return True
        except Exception:
            continue
    return False


def human_type(page: Page, locator, text: str) -> None:
    """Simule une frappe humaine avec des délais réalistes."""
    try:
        locator.click()
        time.sleep(random.uniform(0.15, 0.3))
        for char in text:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.03, 0.09))
        time.sleep(random.uniform(0.15, 0.3))
    except Exception as e:
        logger.debug("Saisie human_type : repli sur fill direct (%s)", e)
        locator.fill(text)


def find_and_fill_login_form(page: Page, auto_submit: bool = True) -> bool:
    """
    Détecte et remplit le formulaire de connexion sur Apec avec plusieurs
    sélecteurs de repli et soumission adaptative.
    """
    logger.debug("Recherche du formulaire de connexion...")

    email_selectors = [
        "xpath=/html/body/div[2]/div/div[1]/div/form/div[3]/input",
        "input[type='email']",
        "input[name='username']",
        "input[name='email']",
        "input#email",
        "input[autocomplete='username']",
        "input[formcontrolname='username']",
        "input[formcontrolname='email']",
        "form input:not([type='hidden']):not([type='checkbox']):not([type='password'])",
    ]

    password_selectors = [
        "xpath=/html/body/div[2]/div/div[1]/div/form/div[4]/input",
        "input[type='password']",
        "input[name='password']",
        "input#password",
        "input[formcontrolname='password']",
    ]

    submit_selectors = [
        "xpath=/html/body/div[2]/div/div[1]/div/form/div[5]/button",
        "button[type='submit']",
        "button:has-text('Se connecter')",
        "button:has-text('Connexion')",
        "form button[type='submit']",
        "form button",
    ]

    # Attente active du formulaire
    email_loc = None
    start_time = time.time()
    while time.time() - start_time < 12:
        dismiss_cookie_banner(page)

        for sel in email_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=800):
                    email_loc = loc
                    logger.debug("Champ identifiant trouvé (%s)", sel)
                    break
            except Exception:
                continue

        if email_loc:
            break
        time.sleep(0.8)

    if not email_loc:
        return False

    # Saisie de l'identifiant
    human_type(page, email_loc, APEC_USERNAME)
    logger.debug("Identifiant renseigné.")

    # Recherche et saisie du mot de passe
    pwd_loc = None
    for sel in password_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=800):
                pwd_loc = loc
                logger.debug("Champ mot de passe trouvé (%s)", sel)
                break
        except Exception:
            continue

    if not pwd_loc:
        logger.error("Champ mot de passe introuvable.")
        return False

    human_type(page, pwd_loc, APEC_PASSWORD)
    logger.debug("Mot de passe renseigné.")

    if not auto_submit:
        logger.debug("Soumission automatique désactivée pour validation dans noVNC.")
        return True

    # Clic sur le bouton de connexion
    submit_loc = None
    for sel in submit_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=800):
                submit_loc = loc
                logger.debug("Bouton de connexion trouvé (%s)", sel)
                break
        except Exception:
            continue

    if submit_loc:
        try:
            submit_loc.hover()
            time.sleep(random.uniform(0.2, 0.4))
            submit_loc.click()
            logger.debug("Formulaire de connexion soumis.")
        except Exception as e:
            logger.warning("Clic sur le bouton de connexion impossible (%s)", e)

    return True


def unlock_form_and_buttons(page: Page) -> None:
    """
    Déverrouille les boutons de formulaire potentiellement désactivés
    par l'interception anti-bot d'Angular.
    """
    try:
        page.evaluate("""
            document.querySelectorAll("button[disabled], input[disabled]").forEach(el => {
                el.disabled = false;
                el.removeAttribute('disabled');
            });
        """)
    except Exception:
        pass


def authenticate_and_update(nouveau_poste: str, cookies_path: Path) -> Tuple[bool, str]:
    """
    Lance Chromium avec profil persistant et empreinte cohérente pour :
    1. Résoudre le challenge ou permettre la connexion.
    2. Valider la session candidat (recherche de apec.user.cookie).
    3. Sauvegarder les cookies pour le Niveau 1 (API REST rapide).
    4. Mettre à jour le poste sur la carte de visite.

    Retourne : (succès: bool, message: str)
    """
    logger.info("Démarrage du navigateur Playwright (profil persistant, headless=%s)...", HEADLESS)

    # Répertoire du profil persistant du navigateur (conserve cache, indexeddb, storage)
    browser_profile_dir = DATA_DIR / "browser_profile"
    browser_profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Configuration Chromium native : pas de faux user-agent contradictoire,
        # drapeaux d'évitement de détection automatisée natifs
        context: BrowserContext = p.chromium.launch_persistent_context(
            user_data_dir=str(browser_profile_dir),
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
            ],
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )

        # Nettoyage subtil de l'indicateur d'automatisation sans altérer les prototypes profonds
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Récupère la première page créée ou en ouvre une
        # Injection préalable des cookies enregistrés ou importés si disponibles
        if cookies_path.exists():
            try:
                with open(cookies_path, "r", encoding="utf-8") as f:
                    raw_cookies = json.load(f)
                if isinstance(raw_cookies, list):
                    pw_cookies = []
                    for c in raw_cookies:
                        if isinstance(c, dict) and "name" in c and "value" in c:
                            item = {
                                "name": c["name"],
                                "value": str(c["value"]),
                                "domain": c.get("domain", "www.apec.fr"),
                                "path": c.get("path", "/"),
                                "secure": c.get("secure", True),
                                "httpOnly": c.get("httpOnly", False),
                            }
                            if c.get("sameSite") and str(c["sameSite"]).lower() in ("lax", "strict", "none"):
                                item["sameSite"] = str(c["sameSite"]).capitalize()
                            pw_cookies.append(item)
                    if pw_cookies:
                        context.add_cookies(pw_cookies)
            except Exception as e:
                logger.warning("Impossible d'injecter les cookies préalables : %s", e)

        # Récupère la page par défaut du contexte persistant ou en crée une
        page: Page = context.pages[0] if context.pages else context.new_page()

        try:
            logger.info("Navigation vers la page du profil APEC...")
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
            time.sleep(3)

            dismiss_cookie_banner(page)

            # Remplir le formulaire
            filled = find_and_fill_login_form(page, auto_submit=True)
            if not filled:
                logger.debug("Formulaire de connexion non présent (session déjà active ou page différente).")

            logger.debug("Vérification de la session utilisateur ('apec.user.cookie')...")
            session_established = False
            captcha_alerted = False

            # Attente jusqu'à 150 secondes pour permettre la validation noVNC
            for attempt in range(150):
                cookies = context.cookies()
                cookie_names = [c["name"] for c in cookies]

                # Seul 'apec.user.cookie' atteste d'une session authentifiée
                if "apec.user.cookie" in cookie_names:
                    session_established = True
                    logger.info("Session utilisateur validée avec succès.")
                    break

                # Détection d'un challenge DataDome ou d'une demande de vérification
                try:
                    content = page.content().lower()
                    is_captcha = (
                        "robot" in content
                        or "glisser" in content
                        or "sécuriser votre accès" in content
                        or "captcha-delivery" in content
                        or "datadome" in content
                    )
                    if is_captcha and not captcha_alerted:
                        captcha_alerted = True
                        logger.warning(
                            "\n========================================================================\n"
                            "⚠️  CHALLENGE DE SÉCURITÉ DÉTECTÉ !\n"
                            "👉 Ouvrez votre navigateur sur : http://localhost:6080 (ou http://<ip>:6080)\n"
                            "1. Résolvez le slider manuellement sur l'écran noVNC.\n"
                            "2. Si nécessaire, cliquez sur 'Se connecter' (le bouton a été déverrouillé).\n"
                            "3. NE RAFRAÎCHISSEZ PAS LA PAGE avec F5.\n"
                            "Le script surveille la connexion en arrière-plan (jusqu'à 150 secondes)...\n"
                            "========================================================================"
                        )
                        # Déverrouille les boutons pour que l'utilisateur puisse cliquer
                        unlock_form_and_buttons(page)
                except Exception:
                    pass

                # Quand le captcha est détecté, on NE SPAMME PAS dismiss_cookie_banner
                # pour ne pas voler le focus de l'utilisateur sur noVNC
                if not captcha_alerted:
                    dismiss_cookie_banner(page)
                else:
                    # En mode alerte noVNC, s'assure régulièrement que les boutons restent cliquables
                    if attempt % 5 == 0:
                        unlock_form_and_buttons(page)

                time.sleep(1)

            # Sauvegarde de capture pour diagnostic (uniquement si LOG_LEVEL=DEBUG)
            if LOG_LEVEL == "DEBUG":
                try:
                    debug_screen = DATA_DIR / "debug_after_login.png"
                    page.screenshot(path=str(debug_screen))
                    logger.debug("Capture d'état sauvegardée dans %s", debug_screen)
                except Exception:
                    pass

            if not session_established:
                logger.warning(
                    "Le cookie 'apec.user.cookie' n'a pas été détecté. Cookies actuels : %s",
                    [c["name"] for c in context.cookies()],
                )
                return False, "Session candidat non établie (apec.user.cookie absent)."

            # Sauvegarde immédiate des cookies acquis
            cookies = context.cookies()
            save_cookies(cookies_path, cookies)
            logger.debug("Nouveaux cookies sauvegardés dans %s", cookies_path)

            time.sleep(2)

            # --- Tentative 1 : Mise à jour directe via l'API interne du navigateur ---
            logger.debug("Tentative de mise à jour via l'API interne du navigateur...")
            get_res = context.request.get(
                API_URL,
                headers={
                    "accept": "application/json, text/plain, */*",
                    "origin": "https://www.apec.fr",
                    "referer": TARGET_URL,
                },
            )

            if get_res.status == 200:
                try:
                    profile_data = get_res.json()
                    ancien_poste = profile_data.get("metierSouhaite", "")
                    logger.info("Poste actuel sur l'Apec : '%s' -> Nouveau poste : '%s'", ancien_poste, nouveau_poste)

                    profile_data["metierSouhaite"] = nouveau_poste

                    logger.debug("Envoi de la mise à jour via POST carteDeVisite...")
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
                            f"Profil Apec mis à jour avec succès via l'API interne du navigateur ! (HTTP {post_res.status})",
                        )
                except Exception as e:
                    logger.debug("Erreur lors de la manipulation du JSON API : %s", e)

            logger.debug("API directe HTTP %s : Passage au plan de repli via l'interface...", get_res.status)

            # --- Tentative 2 : Plan de repli via l'interface graphique Playwright ---
            if "carte-visite" not in page.url:
                logger.debug("Navigation sur la page du profil pour mise à jour dans le formulaire...")
                page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            dismiss_cookie_banner(page)

            poste_input_selectors = [
                "xpath=/html/body/main/apec-profil-cadre/apec-carte-visite/div/div[2]/div/div[1]/form/div[5]/input",
                "input[formcontrolname='metierSouhaite']",
                "input[name='metierSouhaite']",
                "apec-carte-visite form input",
            ]

            poste_input = None
            for sel in poste_input_selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible(timeout=3000):
                        poste_input = loc
                        logger.debug("Champ métier souhaité trouvé (%s)", sel)
                        break
                except Exception:
                    continue

            if poste_input:
                logger.info("Saisie du nouveau poste : '%s'", nouveau_poste)
                poste_input.click()
                poste_input.fill("")
                time.sleep(0.3)
                poste_input.fill(nouveau_poste)
                time.sleep(0.3)

                save_button_selectors = [
                    "xpath=/html/body/main/apec-profil-cadre/apec-carte-visite/div/div[2]/div/div[1]/form/div[9]/button",
                    "button:has-text('Enregistrer')",
                    "apec-carte-visite form button[type='submit']",
                ]

                for sel in save_button_selectors:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            logger.debug("Bouton Enregistrer cliqué (%s)", sel)
                            time.sleep(3)
                            save_cookies(cookies_path, context.cookies())
                            return True, "Profil Apec mis à jour avec succès via l'interface graphique !"
                    except Exception:
                        continue

            return False, f"Échec de la mise à jour (API HTTP {get_res.status} et formulaire introuvable)."

        except Exception as e:
            logger.error("Erreur durant l'exécution Playwright : %s", e)
            try:
                page.screenshot(path=str(DATA_DIR / "debug_error.png"))
            except Exception:
                pass
            return False, f"Erreur Playwright : {e}"

        finally:
            context.close()
            logger.debug("Contexte Playwright fermé.")
