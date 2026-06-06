import atexit
import logging
import socket
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def find_available_port(host, start, end):
    for port in range(start, end + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((host, port))
            sock.close()
            return port
        except OSError:
            sock.close()
            continue
    raise RuntimeError(f"No available port in range {start}-{end}")


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

    configured_port = settings.PORT
    actual_port = find_available_port(settings.HOST, configured_port, configured_port + 10)

    if actual_port != configured_port:
        logger.warning("Port %d in use, using %d instead", configured_port, actual_port)

    port_file = Path(__file__).parent / ".port"
    port_file.write_text(str(actual_port), encoding="utf-8")

    def cleanup():
        port_file.unlink(missing_ok=True)
        logger.debug("Cleanup: removed .port file")

    atexit.register(cleanup)

    from web.app import create_app
    app = create_app()

    logger.info("Starting server on %s:%d", settings.HOST, actual_port)
    app.run(host=settings.HOST, port=actual_port, debug=False)


if __name__ == "__main__":
    main()
