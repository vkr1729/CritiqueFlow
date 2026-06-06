import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    from security.network_guard import activate_network_guard
    activate_network_guard()

    from config.settings import settings

    logger.info("Configuration loaded from .env")
    logger.info("LLM Endpoint: %s", settings.LLM_ENDPOINT[:50] + "..." if len(settings.LLM_ENDPOINT) > 50 else settings.LLM_ENDPOINT)
    logger.info("LLM Model: %s", settings.LLM_MODEL)
    logger.info("Network Guard: %s", "ENABLED" if settings.ENABLE_NETWORK_GUARD else "DISABLED")
    logger.info("Max Iteration Depth: %d", settings.MAX_ITERATION_DEPTH)

    from core.session_store import init_db
    init_db()

    from web.app import create_app
    app = create_app()

    logger.info("Starting server on %s:%d", settings.HOST, settings.PORT)
    app.run(host=settings.HOST, port=settings.PORT, debug=False)


if __name__ == "__main__":
    main()
