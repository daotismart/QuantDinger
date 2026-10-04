"""Reap exited children so long-lived workers do not fill the PID table.

Libraries and sandbox helpers (multiprocessing, native CTP/akshare helpers)
sometimes ``fork()`` without ``wait()``. Compose caps backend PIDs at
``BACKEND_PIDS_LIMIT`` (default 512). Once that table fills, health checks,
SSH, and request workers stop forking and the host looks hung.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_installed = False


def reap_children() -> int:
    """Non-blocking ``waitpid(-1)`` until no exited child remains."""
    if os.name == "nt":
        return 0
    reaped = 0
    while True:
        try:
            pid, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        except OSError:
            break
        if pid <= 0:
            break
        reaped += 1
    return reaped


def _handle_sigchld(_signum, _frame) -> None:
    reap_children()


def _interval_loop(interval_sec: float) -> None:
    while True:
        try:
            reap_children()
        except Exception:
            logger.debug("periodic child reap failed", exc_info=True)
        threading.Event().wait(interval_sec)


def _resolve_interval(interval_sec: Optional[float]) -> float:
    if interval_sec is not None:
        return float(interval_sec)
    raw = os.getenv("QD_CHILD_REAP_INTERVAL_SEC", "15")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 15.0


def install_child_reaper(*, interval_sec: Optional[float] = None) -> bool:
    """Install SIGCHLD plus a periodic reap thread. Idempotent. Unix only.

    If another library already owns ``SIGCHLD`` (Celery prefork parent,
    Gunicorn master), keep that handler and only start the interval thread.
    """
    global _installed
    if os.name == "nt":
        return False
    with _lock:
        if _installed:
            reap_children()
            return False
        previous = signal.getsignal(signal.SIGCHLD)
        if previous in (signal.SIG_DFL, signal.SIG_IGN, None):
            signal.signal(signal.SIGCHLD, _handle_sigchld)
        interval = _resolve_interval(interval_sec)
        if interval > 0:
            thread = threading.Thread(
                target=_interval_loop,
                args=(interval,),
                name="qd-child-reaper",
                daemon=True,
            )
            thread.start()
        _installed = True
        logger.info("Child reaper installed (interval=%.1fs)", max(interval, 0.0))
        return True
