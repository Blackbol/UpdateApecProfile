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
    NOVNC_PORT,
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
        locator.fill("")
        for char in text:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.03, 0.08))
        time.sleep(random.uniform(0.15, 0.3))
        page.keyboard.press("Tab")
    except Exception as e:
        logger.debug("Saisie human_type : repli sur fill direct (%s)", e)
        locator.fill(text)


def is_login_page(page: Page) -> bool:
    """Vérifie si la page courante est une page de connexion."""
    url = page.url.lower()
    return "authentification" in url or "connexion" in url or "login" in url


def is_captcha_present(page: Page) -> bool:
    """
    Détecte la présence d'un challenge anti-bot (DataDome iframe, slider, Cloudflare, etc.).
    """
    try:
        # 1. Présence d'iframe spécifique DataDome / captcha
        if page.locator("iframe[title*='DataDome'], iframe[src*='captcha-delivery']").count() > 0:
            return True
        for frame in page.frames:
            f_url = frame.url.lower()
            if "captcha-delivery" in f_url or "datadome" in f_url:
                return True

        # 2. Indicateurs textuels dans le contenu ou le titre
        content = page.content().lower()
        captcha_indicators = [
            "captcha-delivery.com",
            "datadome",
            "sécuriser votre accès",
            "accès temporairement restreint",
            "glisser pour",
            "glissez pour",
            "veuillez vérifier que vous êtes un humain",
        ]
        if any(ind in content for ind in captcha_indicators):
            return True
    except Exception:
        pass
    return False


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
    while time.time() - start_time < 8:
        dismiss_cookie_banner(page)

        for sel in email_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=500):
                    email_loc = loc
                    logger.debug("Champ identifiant trouvé (%s)", sel)
                    break
            except Exception:
                continue

        if email_loc:
            break
        time.sleep(0.5)

    if not email_loc:
        return False

    # Saisie de l'identifiant s'il n'est pas déjà renseigné
    try:
        current_val = email_loc.input_value()
    except Exception:
        current_val = ""
    if current_val != APEC_USERNAME:
        human_type(page, email_loc, APEC_USERNAME)
        logger.debug("Identifiant renseigné.")

    # Recherche et saisie du mot de passe
    pwd_loc = None
    for sel in password_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=500):
                pwd_loc = loc
                logger.debug("Champ mot de passe trouvé (%s)", sel)
                break
        except Exception:
            continue

    if not pwd_loc:
        logger.error("Champ mot de passe introuvable.")
        return False

    try:
        current_pwd = pwd_loc.input_value()
    except Exception:
        current_pwd = ""
    if not current_pwd:
        human_type(page, pwd_loc, APEC_PASSWORD)
        logger.debug("Mot de passe renseigné.")

    if not auto_submit:
        logger.debug("Soumission automatique désactivée pour validation dans noVNC.")
        return True

    # Déverrouillage préventif avant clic
    unlock_form_and_buttons(page)

    # Clic sur le bouton de connexion
    submit_loc = None
    for sel in submit_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=500):
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
                cookie_items = []
                if isinstance(raw_cookies, list):
                    cookie_items = raw_cookies
                elif isinstance(raw_cookies, dict):
                    if "cookies" in raw_cookies and isinstance(raw_cookies["cookies"], list):
                        cookie_items = raw_cookies["cookies"]
                    else:
                        cookie_items = [{"name": k, "value": v} for k, v in raw_cookies.items()]

                pw_cookies = []
                for c in cookie_items:
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

            logger.debug("Vérification de la session utilisateur...")
            session_established = False
            captcha_alerted = False
            login_attempted = False

            # Attente jusqu'à 150 secondes pour permettre la validation et résolution noVNC
            for attempt in range(150):
                # 1. Vérification challenge Captcha / DataDome
                if is_captcha_present(page):
                    if not captcha_alerted:
                        captcha_alerted = True
                        logger.warning(
                            "\n========================================================================\n"
                            "⚠️  CHALLENGE DE SÉCURITÉ DÉTECTÉ !\n"
                            f"👉 Ouvrez votre navigateur sur : http://localhost:{NOVNC_PORT} (ou http://<ip>:{NOVNC_PORT})\n"
                            "1. Résolvez le slider manuellement sur l'écran noVNC.\n"
                            "2. Si nécessaire, cliquez sur 'Se connecter' (le bouton a été déverrouillé).\n"
                            "3. NE RAFRAÎCHISSEZ PAS LA PAGE avec F5.\n"
                            "Le script surveille la connexion en arrière-plan (jusqu'à 150 secondes)...\n"
                            "========================================================================"
                        )
                    unlock_form_and_buttons(page)
                    time.sleep(1)
                    continue

                if captcha_alerted:
                    logger.info("Challenge de sécurité résolu ! Poursuite du traitement...")
                    captcha_alerted = False
                    time.sleep(1)

                dismiss_cookie_banner(page)

                # 2. Sommes-nous sur une page de connexion ?
                on_login = is_login_page(page)
                if on_login:
                    if not login_attempted or (attempt % 10 == 0):
                        filled = find_and_fill_login_form(page, auto_submit=True)
                        if filled:
                            login_attempted = True
                            logger.debug("Formulaire de connexion renseigné et soumis.")

                # 3. Vérification de la session authentifiée (hors page de connexion)
                cookies = context.cookies()
                cookie_names = [c["name"] for c in cookies]

                if not on_login and "apec.user.cookie" in cookie_names:
                    # Test réel de validité de la session via l'API interne du navigateur
                    try:
                        check_res = context.request.get(
                            API_URL,
                            headers={
                                "accept": "application/json, text/plain, */*",
                                "origin": "https://www.apec.fr",
                                "referer": TARGET_URL,
                            },
                        )
                        if check_res.status == 200:
                            session_established = True
                            logger.info("Session utilisateur validée avec succès.")
                            break
                        elif check_res.status in (401, 403):
                            logger.debug("Session expirée ou non autorisée (HTTP %s).", check_res.status)
                    except Exception as e:
                        logger.debug("Test session API : %s", e)

                    # Vérification alternative si le composant profil est déjà affiché
                    try:
                        if page.locator("apec-carte-visite, input[formcontrolname='metierSouhaite']").count() > 0:
                            session_established = True
                            logger.info("Session utilisateur validée (carte de visite présente).")
                            break
                    except Exception:
                        pass

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
                    "Session candidat non établie après attente. URL actuelle : %s, Titre : '%s'",
                    page.url,
                    page.title(),
                )
                return False, "Session candidat non établie (délai dépassé ou authentification requise)."

            # Sauvegarde immédiate des cookies acquis
            cookies = context.cookies()
            save_cookies(cookies_path, cookies)
            save_cookies(DATA_DIR / "cookie.json", cookies)
            logger.debug("Nouveaux cookies sauvegardés dans %s", cookies_path)

            time.sleep(1)

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
                        save_cookies(cookies_path, context.cookies())
                        save_cookies(DATA_DIR / "cookie.json", context.cookies())
                        return (
                            True,
                            f"Profil Apec mis à jour avec succès via l'API interne du navigateur ! (HTTP {post_res.status})",
                        )
                    else:
                        logger.warning(
                            "Mise à jour via API rejetée (HTTP %s). Repli sur l'interface graphique...",
                            post_res.status,
                        )
                except Exception as e:
                    logger.debug("Erreur lors de la manipulation du JSON API : %s", e)
            else:
                logger.debug("API directe HTTP %s : Passage au plan de repli via l'interface...", get_res.status)

            # --- Tentative 2 : Plan de repli via l'interface graphique Playwright ---
            if "carte-visite" not in page.url:
                logger.debug("Navigation sur la page du profil pour mise à jour dans le formulaire...")
                page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            dismiss_cookie_banner(page)

            poste_input_selectors = [
                "input[formcontrolname='metierSouhaite']",
                "xpath=/html/body/main/apec-profil-cadre/apec-carte-visite/div/div[2]/div/div[1]/form/div[5]/input",
                "xpath=//apec-carte-visite//form//input[@formcontrolname='metierSouhaite']",
                "input[name='metierSouhaite']",
                "apec-carte-visite form input",
            ]

            logger.debug("Attente de l'apparition du champ métier souhaité sur la carte de visite...")
            poste_input = None
            start_wait = time.time()
            while time.time() - start_wait < 30:
                dismiss_cookie_banner(page)
                for sel in poste_input_selectors:
                    try:
                        loc = page.locator(sel).first
                        if loc.is_visible(timeout=1000):
                            poste_input = loc
                            logger.debug("Champ métier souhaité trouvé (%s)", sel)
                            break
                    except Exception:
                        continue
                if poste_input:
                    break
                time.sleep(1)

            if not poste_input:
                try:
                    debug_form = DATA_DIR / "debug_form_not_found.png"
                    page.screenshot(path=str(debug_form))
                    logger.warning(
                        "Formulaire introuvable après 30s. Capture sauvegardée dans %s (URL: %s, Titre: '%s')",
                        debug_form,
                        page.url,
                        page.title(),
                    )
                except Exception:
                    pass
                api_status = get_res.status if "get_res" in locals() else "N/A"
                return False, f"Échec de la mise à jour (API HTTP {api_status} et formulaire introuvable)."

            logger.info("Saisie du nouveau poste : '%s'", nouveau_poste)
            poste_input.click()
            poste_input.fill("")
            time.sleep(0.3)
            poste_input.fill(nouveau_poste)
            time.sleep(0.3)

            save_button_selectors = [
                "button:has-text('Enregistrer')",
                "xpath=/html/body/main/apec-profil-cadre/apec-carte-visite/div/div[2]/div/div[1]/form/div[9]/button",
                "xpath=//apec-carte-visite//form//button[@type='submit']",
                "apec-carte-visite form button[type='submit']",
                "apec-carte-visite form button",
            ]

            save_btn = None
            start_btn_wait = time.time()
            while time.time() - start_btn_wait < 15:
                for sel in save_button_selectors:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=1000):
                            save_btn = btn
                            logger.debug("Bouton Enregistrer trouvé (%s)", sel)
                            break
                    except Exception:
                        continue
                if save_btn:
                    break
                time.sleep(1)

            if save_btn:
                unlock_form_and_buttons(page)
                save_btn.click()
                logger.debug("Bouton Enregistrer cliqué.")
                time.sleep(3)
                save_cookies(cookies_path, context.cookies())
                save_cookies(DATA_DIR / "cookie.json", context.cookies())
                return True, "Profil Apec mis à jour avec succès via l'interface graphique !"
            else:
                logger.warning("Bouton Enregistrer introuvable.")
                return False, "Formulaire trouvé mais bouton Enregistrer introuvable."

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
