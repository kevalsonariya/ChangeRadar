"""ChangeRadar Automatic Website Monitoring Worker.

Runs as a standalone, dedicated background process to periodically check monitored
websites at their configured check intervals, create baseline snapshots, detect
content changes, generate notifications, and extract deadlines.
"""

import argparse
import asyncio
import atexit
import logging
import os
import signal
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session
from .database import SessionLocal, init_db
from .models.models import Website, utc_now
from .services.check_service import check_website

# Logger setup
logger = logging.getLogger("changeradar.worker")

# Lock file location for single-worker instance coordination
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOCK_FILE = BASE_DIR / "changeradar.worker.lock"


def is_pid_running(pid: int) -> bool:
    """Check if a process with the given PID is currently active."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            exit_code = ctypes.c_ulong()
            still_active = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            # STILL_ACTIVE = 259
            return bool(still_active and exit_code.value == 259)
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def is_website_due(
    site: Website,
    now: Optional[datetime] = None,
    min_interval_minutes: int = 1
) -> bool:
    """Determine whether a website is currently due for a scheduled check.

    - Disabled/paused websites (status == 'paused') are always skipped.
    - Websites never checked before (last_checked_at is None) are due immediately.
    - Checked websites are due when elapsed time >= check_interval_minutes.
    """
    if site.status == "paused":
        return False

    if site.last_checked_at is None:
        return True

    now = now or utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    last_checked = site.last_checked_at
    if last_checked.tzinfo is None:
        last_checked = last_checked.replace(tzinfo=timezone.utc)

    interval_minutes = max(min_interval_minutes, int(site.check_interval_minutes or 60))
    due_threshold = last_checked + timedelta(minutes=interval_minutes)

    return now >= due_threshold


def get_due_websites(
    db: Session,
    now: Optional[datetime] = None,
    min_interval_minutes: int = 1
) -> List[Website]:
    """Query and return all active websites that are due for a check."""
    # Query all non-paused websites
    candidates = (
        db.query(Website)
        .filter(Website.status != "paused")
        .order_by(Website.last_checked_at.asc().nullsfirst())
        .all()
    )

    due_list = [
        site for site in candidates
        if is_website_due(site, now=now, min_interval_minutes=min_interval_minutes)
    ]
    return due_list


class MonitoringWorker:
    """Standalone background worker for periodic website monitoring."""

    def __init__(
        self,
        poll_interval: Optional[float] = None,
        request_delay: Optional[float] = None,
        min_interval_minutes: Optional[int] = None,
        lock_file_path: Optional[Path] = None,
        single_instance: bool = True,
    ):
        # Configuration with environment variable overrides
        self.poll_interval = float(
            poll_interval
            if poll_interval is not None
            else os.getenv("CHANGERADAR_WORKER_POLL_INTERVAL", "10.0")
        )
        self.request_delay = float(
            request_delay
            if request_delay is not None
            else os.getenv("CHANGERADAR_WORKER_REQUEST_DELAY", "1.0")
        )
        self.min_interval_minutes = int(
            min_interval_minutes
            if min_interval_minutes is not None
            else os.getenv("CHANGERADAR_WORKER_MIN_INTERVAL", "1")
        )
        self.lock_file_path = lock_file_path or DEFAULT_LOCK_FILE
        self.single_instance = single_instance

        self.running = False
        self._stop_requested = False
        self.cycle_count = 0
        self.in_progress: Set[int] = set()
        self._lock_acquired = False

    def acquire_instance_lock(self) -> bool:
        """Enforce single-worker instance execution via PID lock file."""
        if not self.single_instance:
            return True

        current_pid = os.getpid()

        if self.lock_file_path.exists():
            try:
                content = self.lock_file_path.read_text(encoding="utf-8").strip()
                old_pid = int(content.split()[0])
                if is_pid_running(old_pid):
                    logger.warning(
                        "Another ChangeRadar worker process is already running (PID: %d). "
                        "To prevent duplicate concurrent polling, this instance will exit.",
                        old_pid
                    )
                    return False
                else:
                    logger.info("Removing stale worker lock file from inactive PID %d.", old_pid)
                    self.lock_file_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("Could not read existing lock file: %s. Overwriting.", exc)

        try:
            self.lock_file_path.write_text(
                f"{current_pid} {utc_now().isoformat()}\n",
                encoding="utf-8"
            )
            self._lock_acquired = True
            logger.info("Worker lock acquired (PID: %d, file: %s)", current_pid, self.lock_file_path)
            return True
        except Exception as exc:
            logger.error("Failed to write worker lock file: %s", exc)
            return False

    def release_instance_lock(self):
        """Release worker PID lock on shutdown."""
        if self._lock_acquired and self.lock_file_path.exists():
            try:
                self.lock_file_path.unlink(missing_ok=True)
                self._lock_acquired = False
                logger.info("Worker lock released.")
            except Exception as exc:
                logger.warning("Error releasing worker lock file: %s", exc)

    async def check_single_website(self, website_id: int) -> Dict[str, Any]:
        """Execute a check for a single website with concurrency and error protection."""
        if website_id in self.in_progress:
            logger.warning("Check for website_id=%d already in progress, skipping overlap.", website_id)
            return {"status": "skipped", "message": "Check already in progress"}

        self.in_progress.add(website_id)
        db = SessionLocal()
        try:
            site = db.query(Website).filter(Website.id == website_id).first()
            if not site:
                return {"status": "not_found", "message": f"Website {website_id} not found"}

            logger.info(
                "Checking website: id=%d name='%s' url='%s' interval=%dm",
                site.id,
                site.name,
                site.url,
                site.check_interval_minutes
            )

            # Perform check using existing change orchestration service
            result = await check_website(db, website_id)

            check_status = result.get("status")
            if check_status == "baseline_created":
                logger.info(
                    "Baseline captured: website_id=%d name='%s' snapshot_id=%s",
                    site.id,
                    site.name,
                    result.get("snapshot_id")
                )
            elif check_status == "no_change":
                logger.info("Content unchanged: website_id=%d name='%s'", site.id, site.name)
            elif check_status == "change_detected":
                logger.warning(
                    "CHANGE DETECTED: website_id=%d name='%s' summary='%s'",
                    site.id,
                    site.name,
                    result.get("message")
                )

            return result

        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            logger.warning(
                "Check failed: website_id=%d error='%s' (will retry next interval)",
                website_id,
                detail
            )
            return {"status": "error", "message": detail}

        finally:
            db.close()
            self.in_progress.discard(website_id)

    async def run_once(self) -> Dict[str, Any]:
        """Execute a single polling and evaluation cycle across all due websites."""
        self.cycle_count += 1
        start_time = utc_now()
        stats = {
            "cycle": self.cycle_count,
            "due_count": 0,
            "checked": 0,
            "baselines": 0,
            "unchanged": 0,
            "changes": 0,
            "errors": 0,
            "skipped": 0,
        }

        # Select due websites using short transaction
        db = SessionLocal()
        try:
            due_websites = get_due_websites(
                db,
                now=start_time,
                min_interval_minutes=self.min_interval_minutes
            )
            stats["due_count"] = len(due_websites)
            due_ids = [w.id for w in due_websites]
        finally:
            db.close()

        # Check and process pending deadline reminders on each worker cycle
        db_reminders = SessionLocal()
        try:
            from .services import deadline_reminder_service
            await deadline_reminder_service.process_deadline_reminders(db_reminders, now=start_time)
        except Exception as exc:
            logger.warning("Error checking deadline reminders in worker: %s", exc)
        finally:
            db_reminders.close()

        if stats["due_count"] == 0:
            logger.debug("Cycle #%d: No websites currently due for checking.", self.cycle_count)
            return stats

        logger.info(
            "Cycle #%d started: %d website(s) due for monitoring check.",
            self.cycle_count,
            stats["due_count"]
        )

        # Process each due website sequentially with rate limiting
        for idx, site_id in enumerate(due_ids):
            if self._stop_requested:
                break

            result = await self.check_single_website(site_id)
            res_status = result.get("status")

            stats["checked"] += 1
            if res_status == "baseline_created":
                stats["baselines"] += 1
            elif res_status == "no_change":
                stats["unchanged"] += 1
            elif res_status == "change_detected":
                stats["changes"] += 1
            elif res_status == "error":
                stats["errors"] += 1
            elif res_status in ("skipped", "not_found"):
                stats["skipped"] += 1

            # Request rate-limiting delay between consecutive checks
            if self.request_delay > 0 and idx < len(due_ids) - 1:
                await asyncio.sleep(self.request_delay)

        elapsed = (utc_now() - start_time).total_seconds()
        logger.info(
            "Cycle #%d finished in %.2fs: checked=%d (baselines=%d, unchanged=%d, changes=%d, errors=%d)",
            self.cycle_count,
            elapsed,
            stats["checked"],
            stats["baselines"],
            stats["unchanged"],
            stats["changes"],
            stats["errors"]
        )
        return stats

    async def start(self):
        """Start the continuous background monitoring loop."""
        if self.single_instance and not self.acquire_instance_lock():
            logger.info("Worker cannot start due to existing instance lock.")
            return

        self.running = True
        self._stop_requested = False
        logger.info(
            "ChangeRadar Monitoring Worker started. poll_interval=%.1fs, request_delay=%.1fs, min_interval=%dm",
            self.poll_interval,
            self.request_delay,
            self.min_interval_minutes
        )

        try:
            while self.running and not self._stop_requested:
                try:
                    await self.run_once()
                except Exception as exc:
                    logger.error("Unexpected error in worker cycle: %s", exc, exc_info=True)

                if not self.running or self._stop_requested:
                    break

                logger.debug("Sleeping for %.1fs until next polling cycle...", self.poll_interval)
                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            logger.info("Worker received cancellation signal.")
        finally:
            self.running = False
            self.release_instance_lock()
            logger.info("ChangeRadar Monitoring Worker stopped cleanly.")

    def stop(self):
        """Signal the worker to stop after the current check finishes."""
        self.running = False
        self._stop_requested = True


def setup_signal_handlers(worker: MonitoringWorker, loop: asyncio.AbstractEventLoop):
    """Handle graceful shutdown on SIGINT and SIGTERM."""
    def _shutdown():
        logger.info("Shutdown signal received. Stopping worker...")
        worker.stop()

    for sig_name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, sig_name):
            try:
                loop.add_signal_handler(getattr(signal, sig_name), _shutdown)
            except (NotImplementedError, RuntimeError):
                # On Windows, add_signal_handler may not be supported for all signals in asyncio
                signal.signal(getattr(signal, sig_name), lambda s, f: _shutdown())

    atexit.register(worker.release_instance_lock)


def main():
    """CLI entry point for starting the ChangeRadar Monitoring Worker."""
    parser = argparse.ArgumentParser(
        description="ChangeRadar Dedicated Background Monitoring Worker"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Seconds between worker evaluation cycles (default: 10.0 or env CHANGERADAR_WORKER_POLL_INTERVAL)",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=None,
        help="Rate-limiting delay in seconds between consecutive website fetches (default: 1.0 or env CHANGERADAR_WORKER_REQUEST_DELAY)",
    )
    parser.add_argument(
        "--min-interval",
        type=int,
        default=None,
        help="Minimum allowed check interval in minutes for a website (default: 1 or env CHANGERADAR_WORKER_MIN_INTERVAL)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute a single evaluation cycle and exit immediately",
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help="Disable single-instance PID lock file enforcement",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG logging output",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] [worker] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Initialize tables if necessary
    init_db()

    worker = MonitoringWorker(
        poll_interval=args.poll_interval,
        request_delay=args.request_delay,
        min_interval_minutes=args.min_interval,
        single_instance=not args.no_lock,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    setup_signal_handlers(worker, loop)

    if args.once:
        logger.info("Executing single monitoring cycle...")
        result = loop.run_until_complete(worker.run_once())
        logger.info("Single cycle completed: %s", result)
    else:
        try:
            loop.run_until_complete(worker.start())
        except KeyboardInterrupt:
            logger.info("Worker interrupted by keyboard. Exiting.")
        finally:
            worker.release_instance_lock()


if __name__ == "__main__":
    main()
