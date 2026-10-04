from __future__ import annotations

import os
import time

import pytest

from app.utils import child_reaper


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@pytest.mark.skipif(os.name == "nt", reason="waitpid is Unix-only")
def test_reap_children_collects_exited_fork():
    pid = os.fork()
    if pid == 0:
        os._exit(0)
    deadline = time.time() + 2
    reaped = 0
    while time.time() < deadline:
        reaped += child_reaper.reap_children()
        if reaped or not _pid_exists(pid):
            break
        time.sleep(0.02)
    assert reaped >= 1 or not _pid_exists(pid)


@pytest.mark.skipif(os.name == "nt", reason="SIGCHLD is Unix-only")
def test_install_child_reaper_is_idempotent(monkeypatch):
    monkeypatch.setenv("QD_CHILD_REAP_INTERVAL_SEC", "0")
    child_reaper._installed = False
    assert child_reaper.install_child_reaper(interval_sec=0) is True
    assert child_reaper.install_child_reaper(interval_sec=0) is False
