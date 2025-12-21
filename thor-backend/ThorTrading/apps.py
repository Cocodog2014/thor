import os
import sys

from django.apps import AppConfig


MANAGEMENT_GUARD_COMMANDS = {
    "shell",
    "shell_plus",
    "dbshell",
    "migrate",
    "makemigrations",
    "collectstatic",
    "createsuperuser",
    "test",
    "flush",
    "loaddata",
    "inspectdb",
    "run_thor_stack",
}

SERVER_PROCESS_MARKERS = (
    "runserver",
    "runserver_plus",
    "gunicorn",
    "uvicorn",
    "daphne",
)


def _should_start_background_threads():
    argv = sys.argv or []
    lowered = [arg.lower() for arg in argv]
    argv_blob = " ".join(lowered)

    for marker in SERVER_PROCESS_MARKERS:
        if marker in argv_blob:
            return True, None

    return False, "⏭️ Thor background stack only runs for server processes (runserver/gunicorn/uvicorn/daphne)."


class ThorTradingConfig(AppConfig):
    """Application config keeps legacy DB label but new module path."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ThorTrading"
    verbose_name = "Thor Trading"

    def ready(self):
        """Kick off Thor background stack via a short delayed thread."""
        import logging
        import threading
        import time

        logger = logging.getLogger(__name__)
        argv = sys.argv or []
        lowered_args = [arg.lower() for arg in argv]

        if any(cmd in lowered_args for cmd in MANAGEMENT_GUARD_COMMANDS):
            logger.info(
                "⏭️ Skipping Thor background stack during management command. Args=%s",
                " ".join(argv),
            )
            return

        if "runserver" in lowered_args and os.environ.get("RUN_MAIN") != "true":
            logger.info("⏭️ Django reloader parent process — skipping background tasks.")
            return

        should_start_threads, skip_reason = _should_start_background_threads()
        auto_start = os.environ.get("THOR_STACK_AUTO_START", "1").lower() not in {"0", "false", "no"}

        if not auto_start:
            logger.info(
                "⏭️ THOR_STACK_AUTO_START disabled — background stack will not auto-start in this process.",
            )
            return

        if not should_start_threads:
            logger.info(
                "%s Args=%s",
                skip_reason or "⏭️ Thor background stack suppressed.",
                " ".join(argv),
            )
            return

        try:
            from ThorTrading import globalmarkets_hooks  # noqa: F401
            logger.info("📡 ThorTrading GlobalMarkets hooks registered.")

            def _bootstrap_hooks():
                time.sleep(1.0)
                try:
                    globalmarkets_hooks.bootstrap_open_markets()
                except Exception:
                    logger.exception(
                        "❌ Failed to bootstrap ThorTrading workers for open markets"
                    )

            threading.Thread(
                target=_bootstrap_hooks,
                name="ThorGlobalTimerBootstrap",
                daemon=True,
            ).start()
        except Exception:
            logger.exception("❌ Failed to import ThorTrading GlobalMarkets hooks")

        # Realtime heartbeat now starts from thor_project.apps.ThorProjectConfig
        logger.info("ℹ️ Realtime stack startup handled by thor_project.apps.ThorProjectConfig")

