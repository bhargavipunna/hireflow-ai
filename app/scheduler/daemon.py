"""APScheduler-based daily daemon.

Runs the full Career Copilot pipeline once per day at a configured
time, and keeps running as a foreground process until interrupted.

This is intentionally simple - production deployments would use cron
or systemd timers, but the in-process scheduler is convenient for
local single-machine usage.
"""

from __future__ import annotations

import signal
import sys
import time

from app.config.logger import get_logger
from app.config.settings import MATCH_THRESHOLD, TOP_MATCHES, ensure_dirs

log = get_logger(__name__)


def _run_pipeline_once() -> None:
    """Invoke the full workflow once."""
    from app.graph.workflow import workflow

    state = {
        "resume_text": "",
        "jobs": [],
        "matched_jobs": [],
        "threshold": float(MATCH_THRESHOLD),
        "top_matches_limit": int(TOP_MATCHES),
    }
    try:
        result = workflow.invoke(state)
        n = len(result.get("matched_jobs", []))
        log.info("Scheduled run complete: %d matched jobs", n)
    except Exception as exc:
        log.exception("Scheduled run failed: %s", exc)


def run_scheduler(hour: int = 9, minute: int = 0) -> None:
    """Start the scheduler and block until interrupted."""
    ensure_dirs()
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error(
            "APScheduler is required for the daemon. "
            "Install with: pip install apscheduler"
        )
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _run_pipeline_once,
        CronTrigger(hour=hour, minute=minute),
        id="daily_run",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    def _shutdown(signum, frame):
        log.info("Received signal %s - shutting down scheduler.", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    log.info(
        "Scheduler started. Next daily run at %02d:%02d UTC. Press Ctrl+C to exit.",
        hour, minute,
    )

    # Optional: run once immediately on startup so the user sees activity.
    if "--no-immediate" not in sys.argv:
        log.info("Running an immediate pipeline run on startup...")
        _run_pipeline_once()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
