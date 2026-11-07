import time

import pytest

from studio_ia.core import StudioError
from studio_ia.jobs import TERMINAL, Manager, Store
from studio_ia.pipeline import Request


def wait_job(manager, job_id, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = manager.store.get(job_id)
        if row["state"] in TERMINAL:
            return row
        time.sleep(0.05)
    raise AssertionError("Job did not finish")


def test_queue_and_retry(source, tmp_path, tools):
    manager = Manager(tmp_path / "state", tools)
    try:
        first = manager.submit(Request(str(source), str(tmp_path / "first.mp4")))
        second = manager.submit(Request(str(source), str(tmp_path / "second.mp4")))
        with pytest.raises(StudioError, match="destination"):
            manager.submit(Request(str(source), str(tmp_path / "second.mp4")))
        assert wait_job(manager, first)["state"] == "SUCCEEDED"
        assert wait_job(manager, second)["state"] == "SUCCEEDED"
        again = manager.retry(first, str(tmp_path / "retry.mp4"))
        assert wait_job(manager, again)["state"] == "SUCCEEDED"
        manager.store.remove(first)
        assert (tmp_path / "first.mp4").exists()
    finally:
        manager.close()


def test_cancel_active_and_queued(source, tmp_path, tools):
    manager = Manager(tmp_path / "state", tools)
    try:
        first = manager.submit(Request(str(source), str(tmp_path / "first.mp4"), scale=4))
        second = manager.submit(Request(str(source), str(tmp_path / "second.mp4")))
        time.sleep(0.6)
        manager.cancel(first)
        manager.cancel(second)
        assert wait_job(manager, first)["state"] == "CANCELLED"
        assert wait_job(manager, second)["state"] == "CANCELLED"
        assert not (tmp_path / "first.mp4").exists()
        assert not (tmp_path / "second.mp4").exists()
    finally:
        manager.close()


def test_restart_never_assumes_success(tmp_path, tools):
    store = Store(tmp_path / "state")
    for state in ("RUNNING", "VERIFYING", "QUEUED", "CANCEL_REQUESTED"):
        store.put({"id": state, "state": state})
    manager = Manager(tmp_path / "state", tools)
    try:
        assert all(row["state"] == "INTERRUPTED" for row in manager.store.list())
        with pytest.raises(StudioError, match="déjà ouvert"):
            Manager(tmp_path / "state", tools)
    finally:
        manager.close()
