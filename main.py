import threading
import webview

from backend.api import Api
from backend.app_coordinator import AppCoordinator
from backend.config import config
from backend.constants import MAX_CONNECT_TRIES
from backend.logger import logger, set_log_level, setup_logger
from backend.utils import find_free_port, serve_dist, wait_for_http_server


def main() -> None:
    """Initialize and start the application."""
    default_level = "DEBUG" if config.development_mode else "INFO"
    setup_logger(log_file=config.log_path)
    set_log_level(default_level)

    logger.info("Starting %s v%s", config.app_name, config.app_version)

    coordinator = AppCoordinator()
    coordinator.connect_tracker()

    threading.Thread(
        target=coordinator.connect_discord_rpc,
        kwargs={"max_tries": MAX_CONNECT_TRIES},
        daemon=True,
        name="discord-startup-connect",
    ).start()

    api = Api(coordinator=coordinator)

    if config.frontend_dist_dir.exists():
        port = find_free_port()
        threading.Thread(
            target=serve_dist,
            args=(config.frontend_dist_dir, port),
            daemon=True,
        ).start()
        if not wait_for_http_server("127.0.0.1", port, timeout_seconds=5.0):
            logger.error("Frontend server did not start in time on port %s", port)
        url = f"http://127.0.0.1:{port}/index.html"
    else:
        logger.error("Frontend dist directory not found: %s", config.frontend_dist_dir)
        url = "data:text/html,<html><body><h1>Error: Frontend dist not found</h1></body></html>"

    logger.info("Creating window: %sx%s", config.window_width, config.window_height)

    try:
        webview.create_window(
            config.app_name,
            url=url,
            width=config.window_width,
            height=config.window_height,
            js_api=api,
            confirm_close=False,
            text_select=True,
            zoomable=True,
        )
        webview.start(debug=config.development_mode)
    except Exception:
        logger.exception("Failed to start webview application")
        raise
    finally:
        coordinator.shutdown()


if __name__ == "__main__":
    main()
