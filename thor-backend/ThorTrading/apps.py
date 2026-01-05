from __future__ import annotations
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
}

SERVER_PROCESS_MARKERS = (
    "runserver",
    "runserver_plus",
    "gunicorn",
    "uvicorn",
    "daphne",
)

def ready(self):
    from ThorTrading.studies import load  # noqa

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

        # Ensure study models are registered with Django.
        # (Models live under ThorTrading.studies.models.* and must be imported during app init.)
        from ThorTrading.studies.models import study as _study_models  # noqa: F401
        from ThorTrading.studies import load as _study_modules  # noqa: F401

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

        def _bootstrap_gate():
            # Import lazily inside the worker to keep ready() light/safe.
            try:
                from ThorTrading.studies.futures_total.services import global_market_gate as gm_gate
            except Exception:
                logger.exception("❌ Failed to import ThorTrading GlobalMarketGate")
                return

            logger.info("📡 ThorTrading GlobalMarketGate registered.")

            try:
                time.sleep(1.0)
                gm_gate.bootstrap_open_markets()
            except Exception:
                logger.exception("❌ Failed to bootstrap ThorTrading workers for open markets")

        threading.Thread(
            target=_bootstrap_gate,
            name="ThorGlobalMarketGateBootstrap",
            daemon=True,
        ).start()

        # Realtime heartbeat now starts from thor_project.apps.ThorProjectConfig
        logger.info("ℹ️ Realtime stack startup handled by thor_project.apps.ThorProjectConfig")

