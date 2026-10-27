import time
import signal
import sys
from datetime import datetime
from croniter import croniter

from src.config import RUN_ON_STARTUP, get_cron_expression, logger
from src.main import run

# Gestion de l'arrêt gracieux du conteneur (SIGTERM, SIGINT)
running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("Signal d'arrêt reçu (%s). Fermeture du scheduler...", signum)
    running = False


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def main():
    logger.info("Démarrage du service UpdateApecProfile Scheduler (Cron standard)")

    try:
        cron_expr = get_cron_expression()
    except ValueError as e:
        logger.error("Configuration cron invalide : %s", e)
        sys.exit(1)

    logger.info("Expression cron programmée : '%s'", cron_expr)

    # Exécution immédiate au démarrage si demandé
    if RUN_ON_STARTUP:
        logger.info("Exécution au démarrage demandée (RUN_ON_STARTUP=true)...")
        try:
            run()
        except Exception as e:
            logger.error("Erreur lors de l'exécution initiale : %s", e)

    c_iter = croniter(cron_expr, datetime.now())
    next_run = c_iter.get_next(datetime)
    logger.info("Prochaine exécution prévue le : %s", next_run.strftime("%Y-%m-%d %H:%M:%S"))

    # Boucle de surveillance
    while running:
        now = datetime.now()
        if now >= next_run:
            logger.info("Déclencheur cron atteint (%s). Lancement de la mise à jour...", now.strftime("%Y-%m-%d %H:%M:%S"))
            try:
                run()
            except Exception as e:
                logger.error("Erreur durant l'exécution planifiée : %s", e)

            # Calcul de la prochaine échéance
            next_run = c_iter.get_next(datetime)
            logger.info("Prochaine exécution prévue le : %s", next_run.strftime("%Y-%m-%d %H:%M:%S"))

        time.sleep(2)

    logger.info("Service UpdateApecProfile arrêté proprement.")


if __name__ == "__main__":
    main()
